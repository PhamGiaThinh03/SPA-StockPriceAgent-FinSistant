from app.routes import app

if __name__ == '__main__':
    # Chạy app ở host 0.0.0.0 để có thể truy cập từ bên ngoài container (nếu dùng Docker)
    # port=5000 là cổng mặc định phổ biến cho Flask
    # debug=True để server tự khởi động lại khi có thay đổi code
    app.run(host='0.0.0.0', port=5000, debug=True)