# Components - Thành phần tái sử dụng

## 📦 Mục đích

Folder này chứa các **thành phần (components)** dùng chung cho nhiều demo và pipeline khác nhau.

## 📁 Nội dung

Các components có sẵn (có thể có hoặc không, tùy vào cấu trúc project hiện tại):
- **Data loading** - Load dữ liệu CT scan từ nhiều định dạng khác nhau
- **Preprocessing** - Tiền xử lý ảnh y tế (normalization, resizing, windowing)
- **Model inference** - Chạy inference với các models khác nhau
- **Visualization** - Tạo hình ảnh trực quan kết quả

## 🎯 Cách sử dụng

Các components này được import và sử dụng trong:
- `week4/`, `week5/` - Các tuần thực hành
- `hospital-mlops/` - Pipeline production
- Các demo khác

## 💡 Lưu ý

Nếu folder này trống hoặc chưa có file, components có thể được tổ chức trong từng folder con của project (ví dụ: `hospital-mlops/covid-demo/components/`).
