# Hell Cổ Vật – GitHub Actions miễn phí (public repo)

Python + OpenCV + GitHub Actions, chỉ kiểm tra #Hell mới nhất từ **trang web công khai** https://t.me/s/LMEvents, nhận diện biểu tượng nhiệm vụ Cổ Vật ở dải phía trên ảnh và gửi ảnh/link tới Telegram cá nhân. Không cần Telegram user API, Telegram session, VPS hoặc cloud khác.

## Cài đặt

1. Tạo GitHub repository mới, chọn **Public**. Upload nội dung thư mục này, giữ nguyên `.github/workflows/hell.yml` và `artifact_template.png`.
2. Tạo bot riêng với https://t.me/BotFather (`/newbot`), lưu token cho **bản thân**. Gửi `/start` cho bot.
3. Để lấy `chat_id`, truy cập `https://api.telegram.org/bot<TOKEN>/getUpdates` trên máy tính riêng, đọc `message.chat.id` sau khi gửi `/start`. **KHÔNG** chia sẻ URL có token, không chụp/đăng ảnh màn hình chứa token; đóng tab sau khi sử dụng.
4. GitHub repository → **Settings → Secrets and variables → Actions → New repository secret**: tạo `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID`. Tuyệt đối không commit token vào code/README.
5. Mở tab **Actions → Hell Artifact Notification → Run workflow** để kiểm thử, xem logs chỉ có ID + độ khớp, không có token.
6. Mặc định GitHub tự chạy ở phút 03, 18, 33, 48 UTC. Không cần mở máy tính.

## Chống trùng và an toàn

- Workflow cấp duy nhất `contents: read`; **không thể push/commit code** bằng `GITHUB_TOKEN` của job. `actions/checkout` không giữ token trong git config.
- Dùng Actions cache theo **ID bài Hell** để tránh gửi trùng. Cache có thể bị thu hồi/xóa; trong trường hợp hiếm có thể gửi lại bài cũ. Đây là dedupe *best effort*, không phải bộ nhớ bền vững.
- Chỉ cho chạy `schedule` và `workflow_dispatch`. Không có sự kiện `pull_request` hoặc `pull_request_target`, không chạy code từ PR bên ngoài.
- Chỉ đọc public HTML, không lưu session Telegram hay đăng nhập tài khoản game. Chỉ download ảnh từ các tên miền Telegram CDN trong allowlist và giới hạn 5 MB.
- Secrets vẫn có thể bị lộ nếu **người có quyền ghi sửa mã nguồn/workflow theo hướng độc hại**. Không cấp collaborator write access cho người lạ; bật GitHub 2FA; kiểm tra mỗi thay đổi workflow.
- Actions logs ở repo public cũng công khai: không bật shell tracing, không ghi URL Bot API hoặc response body, không ghi bí mật vào logs. Nếu lộ token, dùng BotFather để revoke token ngay và đổi secret trên GitHub.
- Các GitHub Actions của bên thứ ba (`checkout`, `setup-python`, `cache`) đều được **ghim SHA 40 ký tự**, không dùng tag động.
- `requirements.txt` cố định phiên bản cho tính tái lập, nhưng vẫn cần cập nhật khi có cảnh báo bảo mật.

## Giới hạn cần biết

- Đây là **bản thử nghiệm**, chưa được kiểm tra end-to-end trên GitHub với kênh live vì không có Telegram Bot Token của bạn và môi trường kiểm thử không kết nối trực tiếp Telegram.
- Trang preview HTML của Telegram là nguồn **không chính thức**. Nếu Telegram đổi cấu trúc hoặc giới hạn truy cập từ IP GitHub, bot không đọc được; phải sửa parser hoặc chuyển Telethon sang VPS.
- Template hình đang dùng dựa trên **2 ảnh đều là Cổ Vật**; không có ảnh âm tính chứng minh ngưỡng 0.93 không báo nhầm. Kiểm tra với vài ảnh nhiệm vụ KHÔNG phải Cổ Vật trước khi tin cậy.
- Chỉ đọc bài `#Hell` mới nhất trên trang preview (thay vì quét lịch sử); giới hạn tuổi bài là 58 phút để tránh gửi Hell cũ. Bài của cùng giờ có thể bị bỏ lỡ nếu lịch chạy muộn hoặc bài khác đẩy khỏi preview.
- GitHub scheduled workflows có thể bị trì hoãn/bỏ qua và tự vô hiệu hóa khi public repository không có hoạt động trong 60 ngày. Thỉnh thoảng kiểm tra tab Actions.
- GitHub Actions tiêu chuẩn trên public repos được miễn phí theo quy định hiện hành, nhưng gói/dịch vụ vẫn có thể thay đổi.

## Kiểm tra ảnh trên PC trước khi upload

```
python -m pip install -r requirements.txt
python bot.py test-image --file tests/hell_sample_1.png
python bot.py test-image --file tests/hell_sample_2.png
```

Kết quả hai ảnh này phải có score cao. Để kiểm tra âm tính, chạy `test-image` với các ảnh Hell không có Cổ Vật.
