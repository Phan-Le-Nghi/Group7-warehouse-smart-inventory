# Role nghiệp vụ

## Role tối thiểu đã xác nhận

| Role | Trạng thái | Quyền hạn MVP đã duyệt |
|---|---|---|
| Warehouse Staff | CONFIRMED | Perform Receive, Putaway, Pick, Transfer và Audit count; create discrepancy / Adjust request. |
| Manager | CONFIRMED | View operational records; review exceptions/discrepancy; approve/reject Adjust; view Transfer history; confirm/close sensitive exception flows; create minimum Pick Request work items for Warehouse Staff. |
| Purchasing | CONFIRMED | Provide/view expected quantity/reference và create minimum prepared Receive contexts; không có warehouse adjustment permission. |
| Admin | CONFIRMED | Manage users, role assignments và basic system configuration; không bắt buộc tham gia daily warehouse operations. |

Permission model trên là HUMAN PRODUCT DECISION / MVP ASSUMPTION tại `DEC-017`, không phải verified research finding. Không suy diễn thêm create/edit/delete/override permission ngoài wording đã duyệt. `OQ-020` được resolve bởi human decision này.

Quyền create supporting work item và shared minimum SKU catalog read ở trên là
human-approved usability extension tại `DEC-045`. Chúng không thêm canonical User
Story, không thay đổi actor thực hiện Receive/Putaway/Pick và không cấp stock mutation
cho Purchasing hoặc Manager.
