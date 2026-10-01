# Warehouse & Smart Inventory Management

Repository của Nhóm 10 cho môn MIS3032_1.

## Trạng thái hiện tại

- Giai đoạn: **staging/demo release** tại commit `664d207`.
- Frontend staging: <https://group7-warehouse-smart-inventory.vercel.app>.
- Backend staging: <https://group7-warehouse-smart-inventory.onrender.com>.
- Technology stack đã được human approve: React + TypeScript + Vite, FastAPI,
  SQLAlchemy/Alembic và PostgreSQL.
- Cả 9 canonical Must stories đã được merged và được human thực hiện staging
  smoke. Đây không phải tuyên bố production-grade; long-term production target
  và các giới hạn chưa được quyết định vẫn giữ `TBD`/`OPEN QUESTION`.

## Bối cảnh dự án đã xác nhận

Dự án giải quyết bài toán kiểm soát nhập kho, xuất/lấy hàng, chuyển kho và tồn kho.

Quy trình đã được giảng viên xác nhận:

`Receive -> Putaway -> Pick -> Transfer -> Adjust -> Audit`

Các role tối thiểu gồm Warehouse Staff, Manager, Purchasing và Admin. Các hướng AI hiện tại gồm Inventory Q&A, Explain inventory anomalies và Reorder recommendation.

## Bản đồ repository

- [`vault/`](vault/00-index.md): tri thức canonical của dự án và nguồn sự thật duy nhất.
- [`docs/`](docs/00-project-index.md): tài liệu phục vụ môn học/báo cáo và theo dõi artifact.
- [`apps/`](apps/README.md): frontend/backend đã triển khai cho staging/demo cùng
  hướng dẫn chạy, kiểm tra và deployment.
- [`docs/07-release/`](docs/07-release/): checklist và release notes của staging/demo release hiện tại.
- [`PLANS.md`](PLANS.md): kế hoạch triển khai hiện tại và các cổng phê duyệt.
- [`AGENTS.md`](AGENTS.md): quy tắc làm việc bền vững cho phát triển có AI hỗ trợ.

Thông tin còn thiếu hoặc chưa có nguồn hỗ trợ phải được đánh dấu rõ là `TBD`, `ASSUMPTION` hoặc `OPEN QUESTION`.
