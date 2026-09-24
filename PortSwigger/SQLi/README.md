# SQL Injection Report

## Overview
SQL Injection (SQLi) là 1 lỗ hổng bảo mật web cho phép attacker can thiệp vào các query mà application gửi đến database, từ đó attacker có thể truy cập, sửa hoặc xóa data trái phép.

## Root Cause
**User input** bị nối vào query thay vì được xử lí tách biệt giữa code và data, làm ảnh hưởng cấu trúc SQL.

## Example 

* Cho URL với query tương ứng: `https://insecure-website.com/products?category=Gifts`, `SELECT * FROM products WHERE category = 'Gifts' AND released = 1`

* Query này hiển thị các sản phẩm thuộc danh mục **Gifts** (điều kiện `category = 'Gifts'`) và sản phẩm đó đang được phát hành (điều kiện `released = 1`). Tuy nhiên nếu sửa URL: `https://insecure-website.com/products?category=Gifts'--` 

* Lúc này query bị biến đổi: `SELECT * FROM products WHERE category = 'Gifts'--' AND released = 1`

* Vì `--` sẽ comment toàn bộ đoạn code phía sau nên điều kiện `released = 1` không được áp dụng dẫn đến attacker sẽ truy cập được toàn bộ sản phẩm ngay cả khi chúng không được phát hành.

## Types of SQLi
* **In-band SQLi:** Dữ liệu truy vấn trả về trực tiếp trên giao diện web.
  * **UNION-based**
    * Mục đích: Ghép thêm kết quả từ bảng khác vào kết quả ban đầu.
    * Điều kiện: 2 câu lệnh phải trả về cùng số lượng cột và kiểu dữ liệu ở các cột phải tương thích.
    * Quy trình: Xác định số cột -> Xác định cột chứa string -> Trích xuất dữ liệu
  * **Error-based**
    * Mục đích: Kích hoạt thông báo lỗi của CSDL để ép hiển thị dữ liệu nhạy cảm ra màn hình.
    * Payload mẫu: `CAST((SELECT version()) AS int)`
* **Blind SQLi:** Web không in trực tiếp dữ liệu ra màn hình, phải suy đoán gián tiếp.
  * **Boolean-based**
    * Mục đích: Dựa vào khác biệt nội dung trang web khi mệnh đề True/False.
    * Payload mẫu: `TrackingId=xyz' AND '1'='1` (Trang có chữ "Welcome"), `TrackingId=xyz' AND '1'='2` (Trang mất chữ "Welcome").
    * Khai thác trích xuất từng ký tự: `SUBSTRING((SELECT password FROM users WHERE username='administrator'), 1, 1) = 's'`
  * **Error-triggered based**
    * Mục đích: Dựa trên kích hoạt lỗi có điều kiện.
    * Cách thực hiện: dùng cấu trúc `CASE WHEN` ép lỗi database (chia cho 0, cast sai) nếu True trang web sẽ trả về HTTP 500, ngược lại False trả về HTTP 200.
  * **Time-based**
    * Mục đích: Ép database sleep trong một khoảng thời gian nếu điều kiện True.
* **Out-of-band SQLi (OAST):** Ép database gửi request DNS hoặc HTTP ra server bên ngoài khi không thấy kết quả phản hồi nào từ web.

## How to detect SQLi
Ta có thể phát hiện SQLi bằng cách thực hiện 1 loạt cách kiểm tra trên các điểm input:
* Kí tự `'` và quan sát **respones**.
* Gửi 2 payload vào tham số, original value và different value, nếu 2 **respones** khác nhau chứng tỏ database bị ảnh hưởng.
* Các điều kiện logic `OR 1=1` và `OR 1=2` rồi quan sát **respones**.
* Payload tạo **time delays**, theo dõi sự khác biệt thời gian phản hồi.
* Các payload OAST được thiết kế để tương tác ngoài luồng, giám sát mọi phát sinh.

## DBSM
Mỗi DBSM khác nhau có syntax khác nhau, vì vậy cần tra cheat sheet. 
`https://portswigger.net/web-security/sql-injection/cheat-sheet`
