# Kịch bản thuyết trình (theo bản slide Canva 19 trang)

Tổng thời lượng dự kiến: **24:20** (khoảng 2.794 từ, nói khoảng 130 từ/phút), cộng 2–3 phút nếu demo → khoảng 25 phút.

Chia người nói (đổi tên theo phân công của nhóm):

- **Người 1**: slide 1–7, khoảng 7:10
- **Người 2**: slide 8–12, khoảng 8:50
- **Người 3**: slide 13–19, khoảng 8:20

Chữ trong *[ngoặc vuông]* là gợi ý hành động, không đọc thành tiếng.

## Đề xuất sửa slide trước khi trình bày

- **Slide 17, Hạn chế 2**: "chưa đánh giá ngoài mẫu" không còn đúng (nhóm đã có backtest 2011 → 2012). Đề xuất:
  "DSS dựa trên trung bình lịch sử, chưa dự báo; backtest 2011→2012 chỉ bắt 58,5% giờ Cao (hiệu chỉnh mức: 90%)".
- **Slide 17, Hướng phát triển 2**: đề xuất "Mô hình dự báo (hồi quy, chuỗi thời gian), so sánh bằng khung kiểm định ngoài mẫu đã có".
- **Slide 16**: nên thêm 2–3 con số lớn (67/67 kiểm thử đạt, 13/13 phép đối chiếu ETL, backtest 58,5% → 90% giờ Cao) để người nghe nhìn thấy điều đang nói.
- **Slide 18**: có thể thêm một dòng tóm tắt kết luận phía trên "Questions & Discussion" (kịch bản đã nói phần tóm tắt ở slide này).

## Slide 1: Đề tài  ·  0:00 → 0:30  ·  Người 1

Em chào thầy và các bạn. Nhóm 22 xin trình bày bài tập lớn môn Kho dữ liệu và Hệ hỗ trợ quyết định, với đề tài: xây dựng kho dữ liệu và hệ hỗ trợ quyết định chuẩn bị xe cho hệ thống xe đạp công cộng.

## Slide 2: Danh sách thành viên  ·  0:30 → 0:50  ·  Người 1

Nhóm gồm ba thành viên: bạn Trần Gia Bảo Anh, bạn Nguyễn Tiến Bách và bạn Hứa Thanh Tâm.

## Slide 3: Nội dung trình bày  ·  0:50 → 1:30  ·  Người 1

Bài trình bày gồm bốn phần. *[chỉ lần lượt 01 đến 04]* Phần một là bài toán và dữ liệu. Phần hai là cách nhóm xây dựng kho dữ liệu: kiến trúc, thiết kế Star Schema và quy trình ETL. Phần ba là phân tích OLAP trên dashboard và hệ hỗ trợ quyết định, đây là phần trọng tâm. Phần bốn là đánh giá, hạn chế và hướng phát triển.

## Slide 4: Bài toán  ·  1:30 → 2:50  ·  Người 1

Hệ thống xe đạp công cộng cho phép người dân thuê xe ở một trạm và trả ở trạm khác. Khó khăn của người vận hành là nhu cầu thay đổi liên tục. *[chỉ bốn gạch đầu dòng]* Nó thay đổi theo thời gian trong ngày, theo loại ngày là ngày đi làm hay ngày nghỉ, theo điều kiện môi trường như thời tiết, nhiệt độ, và theo nhóm người dùng.

Vì vậy mỗi tối, người vận hành phải trả lời một câu hỏi rất cụ thể. *[chỉ khung câu hỏi]* "Ngày mai là ngày đi làm, trời quang. Giờ nào cần thêm xe và nhân sự, và phải chuẩn bị xong trước mấy giờ?"

Trả lời sai theo hướng nào cũng tốn kém: thiếu xe giờ cao điểm thì mất khách, thừa xe giờ vắng thì lãng phí. Mục tiêu của nhóm là xây dựng một hệ thống trả lời được câu hỏi này dựa trên dữ liệu lịch sử.

## Slide 5: Dữ liệu: nguồn  ·  2:50 → 4:10  ·  Người 1

Nhóm sử dụng bộ Bike Sharing Dataset trên UCI Machine Learning Repository. Dữ liệu được tổng hợp từ lịch sử chuyến đi của hệ thống Capital Bikeshare ở Washington D.C., kết hợp thêm thông tin thời tiết và lịch ngày lễ, trong hai năm từ đầu 2011 đến hết 2012.

*[chỉ bảng nhỏ phía trên]* Bộ dữ liệu có hai tệp. Tệp hour có 17.379 bản ghi theo giờ, là nguồn chính để nạp vào bảng sự kiện. Tệp day có 731 bản ghi theo ngày; nhóm không nạp tệp này mà chỉ dùng để đối chiếu sau khi chạy ETL.

*[chỉ bảng thuộc tính bên phải]* Các thuộc tính được chia thành nhóm: thời gian như năm, tháng, giờ, thứ, ngày lễ; môi trường như mùa, thời tiết, nhiệt độ, độ ẩm, gió; người dùng gồm số lượt của khách vãng lai và khách đăng ký; và kết quả là tổng lượt thuê. Cách chia nhóm này chính là cơ sở để thiết kế các chiều của kho ở phần sau.

## Slide 6: Dữ liệu: số liệu và chất lượng  ·  4:10 → 5:40  ·  Người 1

Một vài con số tổng quan. *[chỉ bốn ô trên]* 17.379 giờ quan sát trong 731 ngày, tổng 3,29 triệu lượt thuê. Năm 2012 tăng gần 65 phần trăm so với 2011, và 81 phần trăm lượt thuê là của khách đăng ký.

*[chỉ biểu đồ]* Biểu đồ theo tháng cho thấy hai điều: năm 2012, đường xanh, nằm cao hơn hẳn năm 2011 ở mọi tháng; và cả hai năm đều có dạng mùa vụ, thấp vào mùa đông, cao vào mùa hè và đầu thu.

*[chỉ khung bên phải]* Trước khi thiết kế, nhóm khảo sát chất lượng dữ liệu và tìm ra bốn vấn đề. Thiếu 165 giờ, rải trên 76 ngày. 22 giờ có độ ẩm bằng 0, là lỗi cảm biến, nhóm chuyển thành NULL. Mưa lớn chỉ có 3 giờ quan sát, nên được gắn cờ ít dữ liệu. Và nhãn mùa của nguồn lệch so với mùa thực tế. Nguyên tắc của nhóm là không âm thầm xóa dữ liệu, mà đánh dấu các vấn đề này ngay trong kho.

## Slide 7: Kiến trúc  ·  5:40 → 7:10  ·  Người 1

Phần hai, xây dựng kho dữ liệu. Đầu tiên là kiến trúc tổng thể. *[chỉ theo mũi tên từ trái sang phải, rồi xuống]*

Dữ liệu đi từ hai tệp CSV qua quy trình ETL viết bằng Python, gồm extract, transform, load và validate, rồi vào PostgreSQL. Trong PostgreSQL, kho nằm ở schema dw theo mô hình Star Schema, kèm một view đã nối sẵn tên v_rentals_flat.

API viết bằng FastAPI chỉ có quyền đọc kho. Nó cung cấp các truy vấn OLAP, KPI, phân tích khí hậu và nhóm API cho DSS. *[chỉ khối xanh lá]* Mô hình DSS được tách thành một module Python riêng, nhận dữ liệu từ API, tính ngưỡng, phân loại và đưa khuyến nghị. Vì tách khỏi cơ sở dữ liệu nên mô hình này kiểm thử được độc lập.

Cuối cùng, dashboard React gọi API qua JSON, gồm năm trang và bộ lọc dropdown, phục vụ người quản lý vận hành và nhà phân tích. Ý chính: kho dữ liệu là nguồn duy nhất cho cả phân tích lẫn ra quyết định. Phần tiếp theo, bạn *[tên người 2]* sẽ trình bày thiết kế kho.

## Slide 8: Thiết kế kho: Star Schema  ·  7:10 → 9:10  ·  Người 2

Cảm ơn bạn. Để thiết kế kho, nhóm áp dụng quy trình bốn bước của Kimball.

Bước một, quy trình nghiệp vụ là việc thuê xe. Bước hai, quan trọng nhất, là chọn độ hạt. Nhóm chọn độ hạt là một giờ của một ngày, mức chi tiết nhỏ nhất mà nguồn có. Lý do: giá trị của hệ hỗ trợ quyết định nằm ở chỗ phân biệt 8 giờ sáng với 2 giờ chiều; nếu gộp lên mức ngày thì thông tin cao điểm mất hẳn.

Bước ba là các chiều. *[chỉ dim_date]* Chiều Ngày có phân cấp năm, quý, tháng, ngày, cùng các cờ cuối tuần, ngày lễ, ngày làm việc; nhóm thêm cột số giờ có bản ghi và cờ ngày đủ 24 giờ để đánh dấu ngày thiếu dữ liệu. *[chỉ dim_hour]* Chiều Giờ có 24 dòng và khung giờ. *[chỉ dim_weather]* Chiều Thời tiết có 4 mức.

Bước bốn là bảng sự kiện. *[chỉ fact_rentals]* Mỗi dòng là một giờ, nối với ba chiều qua khóa ngoại theo quan hệ một nhiều. Độ đo chính là lượt thuê của khách vãng lai, khách đăng ký và tổng; đây là các độ đo cộng được. Nhiệt độ, độ ẩm, gió thì không cộng được mà lấy trung bình. Cột instant_id giữ mã bản ghi gốc để truy vết về nguồn.

Vì sao Star mà không Snowflake? Vì các chiều rất nhỏ, chỉ 731, 24 và 4 dòng. Chuẩn hóa thêm không tiết kiệm được gì mà chỉ làm truy vấn phải nối nhiều bảng hơn.

## Slide 9: Quy trình ETL  ·  9:10 → 10:50  ·  Người 2

Tiếp theo là quy trình ETL, chạy bằng đúng một lệnh. *[chỉ lần lượt từng khối]*

Extract đọc hai tệp CSV. Transform làm sạch dữ liệu: kiểm tra miền giá trị, kiểm tra lịch nhất quán, ví dụ cột thứ phải khớp với ngày, xử lý độ ẩm lỗi, rồi dựng ba chiều và bảng sự kiện. Load dùng lệnh COPY của PostgreSQL trong một giao dịch duy nhất, nên nếu lỗi ở bất kỳ bảng nào thì rollback toàn bộ, kho không bao giờ ở trạng thái nạp dở.

*[chỉ khối Validate màu xanh]* Bước nhóm muốn nhấn mạnh là Validate. Sau khi nạp, hệ thống tự đối chiếu 13 tiêu chí với nguồn và ghi ra một báo cáo; cả 13 đều đạt. Bằng chứng mạnh nhất là phép đối chiếu với tệp day: tệp này không dùng để nạp, nhưng tổng lượt thuê theo từng ngày trong kho khớp với nó ở cả 731 ngày. Tức là dữ liệu trong kho đã được kiểm chứng bằng một nguồn độc lập.

## Slide 10: Dashboard: 5 trang và các phép OLAP  ·  10:50 → 12:10  ·  Người 2

Phần ba, phân tích OLAP. Dashboard chia thành năm trang theo nhóm câu hỏi. *[chỉ cột trái]* Tổng quan, Theo thời gian, Thời tiết và khí hậu, Bảng pivot, và Hỗ trợ quyết định.

*[chỉ cột phải]* Dashboard hỗ trợ đủ năm phép OLAP. Roll-up và drill-down: trên biểu đồ xu hướng, bấm vào một năm để khoan xuống quý, tháng, ngày, giờ, và đi ngược lên để gộp lại. Slice và dice: thanh bộ lọc dropdown dùng chung cho mọi trang; chọn một năm là slice, chọn kết hợp năm, mùa, thời tiết là dice. Pivot: trang Bảng pivot cho người dùng tự chọn hàng, cột và độ đo.

## Slide 11: Tổng quan và nhu cầu theo thời gian  ·  12:10 → 14:10  ·  Người 2

*[chỉ ảnh Tổng quan]* Trang Tổng quan có tám chỉ số chính. Tổng 3,29 triệu lượt thuê, trung bình khoảng 190 lượt mỗi giờ. Giờ đông nhất là 17 giờ, giờ vắng nhất là 4 giờ sáng. Khách đăng ký chiếm 81 phần trăm. Bên dưới là biểu đồ xu hướng theo năm, nơi thực hiện roll-up và drill-down.

*[chỉ ảnh Nhu cầu theo thời gian]* Trang này cho kết quả quan trọng nhất. *[chỉ biểu đồ đường]* Ngày làm việc có hai đỉnh nhọn lúc 8 giờ sáng và 17 giờ chiều, đúng giờ đi làm và tan tầm. Ngày nghỉ khác hẳn: chỉ có một đỉnh tròn kéo dài khoảng từ 12 đến 14 giờ. Giữa giờ đông nhất và vắng nhất chênh nhau hơn 70 lần.

Điều thú vị là tổng lượt thuê theo ngày của hai loại ngày gần bằng nhau, khoảng 4.600 và 4.300 lượt. Nếu chỉ nhìn theo ngày thì hai loại ngày trông như nhau, nhưng phân bố trong ngày khác hoàn toàn. *[chỉ biểu đồ cột cuối]* Biểu đồ theo nhóm khách cũng cho thấy: khách đăng ký tạo ra hai đỉnh đi làm, còn khách vãng lai tập trung vào buổi trưa và chiều.

Kết luận: DSS phải phân loại theo từng giờ của từng loại ngày, không thể dùng một con số cho cả ngày.

## Slide 12: Thời tiết và khí hậu, Bảng pivot  ·  14:10 → 16:00  ·  Người 2

*[chỉ ảnh Thời tiết và khí hậu]* Về thời tiết: so với trời quang, sương mù làm giảm khoảng 15 phần trăm lượt thuê mỗi giờ, còn mưa hoặc tuyết nhẹ làm giảm 45,5 phần trăm, tức gần một nửa.

Về khí hậu: nhiệt độ tương quan dương rõ, hệ số 0,63 ở mức ngày; trời ấm thì nhiều người đạp xe hơn. Độ ẩm là một ví dụ đáng chú ý: ở mức giờ, hệ số tương quan là âm 0,33, trông như độ ẩm làm giảm nhu cầu; nhưng gộp lên mức ngày thì chỉ còn âm 0,11. Nguyên nhân là ban đêm vừa ẩm hơn vừa vắng khách, nên giờ trong ngày là biến gây nhiễu. Tương quan không phải nhân quả.

*[chỉ ảnh Bảng pivot]* Trang Bảng pivot cho phép xoay dữ liệu tùy ý. Ví dụ trên slide là tháng theo hàng, thời tiết theo cột, độ đo là trung bình lượt thuê mỗi giờ, ô càng đậm thì càng đông. Người dùng có thể đổi hàng, cột và độ đo mà không cần viết SQL.

Từ những quy luật này, bạn *[tên người 3]* sẽ trình bày cách nhóm biến chúng thành quyết định.

## Slide 13: DSS: mô hình xếp mức  ·  16:00 → 18:00  ·  Người 3

Cảm ơn bạn. Câu hỏi đặt ra cho hệ hỗ trợ quyết định là: làm sao nói một giờ là Cao, Trung bình hay Thấp một cách có căn cứ? Mô hình có bốn bước. *[chỉ lần lượt 01 đến 04]*

Bước một, chia nhóm. Dữ liệu lịch sử được chia theo giờ, loại ngày và thời tiết, đúng ba yếu tố vừa thấy ảnh hưởng mạnh nhất.

Bước hai, tính ngưỡng. Nhóm không tự đặt ngưỡng mà lấy từ chính dữ liệu: phân vị 33 và 67 của toàn bộ lượt thuê theo giờ, ra hai ngưỡng là 70 và 225 lượt. Vì sao dùng phân vị mà không dùng trung bình cộng trừ độ lệch chuẩn? Vì phân phối lượt thuê lệch phải rất mạnh: nhiều giờ đêm gần bằng 0 và một ít giờ cao điểm rất lớn. Phân vị chia mỗi mức khoảng một phần ba số giờ, cân đối hơn.

Bước ba, xếp mức. *[chỉ khối 03]* So trung bình của từng nhóm với hai ngưỡng: dưới 70 lượt mỗi giờ là Thấp, từ 70 đến 225 là Trung bình, trên 225 là Cao.

Bước bốn, cảnh báo. Gộp các giờ Cao liền nhau thành một khung cảnh báo, và tính giờ phải chuẩn bị xong là một tiếng trước khi khung bắt đầu. Mỗi mức đi kèm một khuyến nghị: Thấp thì tranh thủ bảo trì xe, Trung bình thì theo dõi, Cao thì chuẩn bị thêm xe và nhân sự.

## Slide 14: DSS: kết quả  ·  18:00 → 19:40  ·  Người 3

Đây là câu trả lời cho câu hỏi ở đầu bài. Ngày mai là ngày làm việc, trời quang. *[chỉ biểu đồ trái và các thẻ đỏ]* DSS báo hai khung cao điểm. Khung sáng từ 7 đến 10 giờ, đỉnh lúc 8 giờ với khoảng 500 lượt mỗi giờ, phải chuẩn bị xong trước 6 giờ sáng. Khung chiều từ 16 đến 21 giờ, đỉnh lúc 17 giờ với gần 575 lượt, chuẩn bị xong trước 15 giờ.

*[chỉ biểu đồ phải]* Nếu ngày mai là ngày nghỉ thì chỉ có một khung dài từ 10 giờ đến 20 giờ, đỉnh 12 đến 13 giờ, chuẩn bị trước 9 giờ.

Kết quả này có phụ thuộc vào việc chọn ngưỡng không? Nhóm đã phân tích độ nhạy: đổi ngưỡng sang phân vị 25 và 75, hoặc chỉ dùng dữ liệu năm 2012, thì lõi cao điểm 7 đến 8 giờ và 16 đến 19 giờ vẫn giữ nguyên. Khi mưa nhẹ, số giờ Cao giảm từ 8 xuống 3, nhưng 8 giờ và 17, 18 giờ vẫn là Cao. Tức là khuyến nghị ổn định, không phải do may mắn khi chọn tham số.

## Slide 15: DSS: nhóm khách và từng thứ  ·  19:40 → 21:20  ·  Người 3

Ngoài mức nhu cầu, DSS còn có hai mở rộng giúp quyết định cụ thể hơn.

Thứ nhất là nhóm khách cần phục vụ. *[chỉ khung "Nhóm khách → loại hỗ trợ"]* Xe là dùng chung, nên mức chuẩn bị vẫn tính theo tổng lượt. Nhưng tỷ lệ khách vãng lai cho biết cần loại hỗ trợ nào. Cao điểm ngày làm việc chỉ có 4 đến 13 phần trăm khách vãng lai, gần như toàn người đi làm có thẻ, nên việc cần làm là đủ xe đúng giờ. Cao điểm cuối tuần có khoảng 35 phần trăm khách vãng lai, nhiều người lần đầu dùng, nên cần thêm người hướng dẫn và hỗ trợ thanh toán.

Thứ hai là chọn theo thứ trong tuần. *[chỉ ảnh dashboard bên trái]* Người dùng có thể chọn nhiều thứ, ví dụ thứ sáu và thứ bảy, và mỗi thứ có kế hoạch riêng. Kết quả cho thấy điều mà nhóm "ngày làm việc" che mất: thứ sáu có khung chiều bắt đầu từ 12 giờ, nên phải chuẩn bị trước 11 giờ chứ không phải 15 giờ. Thứ bảy chỉ có một khung từ 10 đến 20 giờ, chuẩn bị trước 9 giờ, và có tới hơn một phần ba là khách vãng lai.

## Slide 16: Đánh giá  ·  21:20 → 22:50  ·  Người 3

Phần bốn, đánh giá. Nguyên tắc của nhóm là mọi kết quả đều được kiểm chứng bằng cách đối chiếu với dữ liệu nguồn. Hệ thống có 67 kiểm thử tự động và tất cả đều đạt. *[chỉ lần lượt bốn ô]*

Với ETL: kiểm tra số dòng, tổng lượt thuê được bảo toàn, khóa ngoại hợp lệ, và dữ liệu sai miền bị từ chối. Với OLAP và API: KPI phải khớp tổng nguồn, tổng các quý phải bằng tổng năm, và chuỗi SQL injection phải vô hại. Với mô hình DSS: kiểm tra biên phân loại, việc gộp khung cảnh báo, xử lý nhóm ít dữ liệu, chạy được mà không cần cơ sở dữ liệu. Và DSS trên kho: ngưỡng và trung bình nhóm phải khớp với số tính độc lập bằng pandas từ tệp hour.

Ngoài ra, nhóm kiểm định mô hình ngoài mẫu: chỉ học trên năm 2011 rồi dự báo mức cho từng giờ của năm 2012. Mô hình đúng khoảng 70 phần trăm, nhưng chỉ bắt được 58,5 phần trăm số giờ Cao, vì nhu cầu năm 2012 tăng khoảng 1,63 lần. Khi thêm hiệu chỉnh mức theo sai số 30 ngày gần nhất, tỷ lệ bắt giờ Cao tăng lên 90 phần trăm. API phản hồi dưới 0,25 giây, và hệ thống đáp ứng đủ 10 yêu cầu chức năng, 7 yêu cầu phi chức năng.

## Slide 17: Hạn chế và hướng phát triển  ·  22:50 → 24:00  ·  Người 3

Nhóm cũng nhìn nhận các hạn chế. *[chỉ cột Hạn chế]* Lớn nhất là dữ liệu chỉ ở mức toàn hệ thống, không có trạm và số xe sẵn có, nên DSS chỉ khuyến nghị mức độ, chưa tính được cần bao nhiêu xe ở trạm nào. Thứ hai, DSS dựa trên trung bình lịch sử, chưa phải mô hình dự báo, nên bị tụt lại khi nhu cầu tăng như kiểm định vừa cho thấy. Thứ ba, dữ liệu là tĩnh, chỉ hai năm, và mưa lớn gần như không có quan sát. Thứ tư, hệ thống chưa có xác thực người dùng và chưa triển khai lên máy chủ.

*[chỉ cột Hướng phát triển]* Hướng phát triển tương ứng: thêm chiều Trạm và số xe để gợi ý số xe cần điều phối; xây dựng mô hình dự báo như hồi quy, chuỗi thời gian, và so sánh với mô hình hiện tại bằng khung kiểm định ngoài mẫu đã có; nạp dữ liệu tăng dần theo ngày; và tích hợp dự báo thời tiết để hệ thống tự chọn tình huống cho ngày mai.

## Slide 18: Questions & Discussion  ·  24:00 → 24:10  ·  Người 3

Tóm lại, nhóm đã xây dựng trọn chuỗi từ dữ liệu thô đến quyết định: kho dữ liệu được đối chiếu 13 trên 13 với nguồn, dashboard đủ năm phép OLAP, và DSS cho biết giờ nào cần chuẩn bị, trước mấy giờ, cho nhóm khách nào. Nhóm em xin sẵn sàng nhận câu hỏi từ thầy và các bạn.

## Slide 19: Thank You  ·  24:10 → 24:20  ·  Người 3

*[Sau phần hỏi đáp]* Nhóm em xin cảm ơn thầy và các bạn đã lắng nghe.

---

**Tùy chọn: demo trực tiếp (thêm 2–3 phút, chèn sau slide 15).** Mở trang Hỗ trợ quyết định:
1. Chọn "Ngày làm việc" + "Quang đãng" → hai khung đỏ và giờ "chuẩn bị trước".
2. Đổi thời tiết sang "Mưa nhẹ" → số giờ Cao giảm, nhưng 8h và 17–18h vẫn Cao.
3. Chọn T6 + T7 ở chế độ "Từng ngày" → khung chiều thứ sáu bắt đầu từ 12h.
4. Kéo xuống phần kiểm định ngoài mẫu → bảng 9 thí nghiệm.

## Câu hỏi có thể gặp

**Vì sao không dùng mô hình học máy?**  
Mục tiêu là DSS dựa trên kho dữ liệu và minh bạch: người vận hành hiểu vì sao một giờ là Cao. Khung kiểm định ngoài mẫu đã có, nên có thể so một mô hình học máy với mô hình hiện tại trên cùng thước đo; đó là hướng phát triển.

**Vì sao chọn phân vị 33/67?**  
Phân phối lệch phải mạnh nên trung bình ± độ lệch chuẩn cho ba mức mất cân đối. Phân vị chia mỗi mức khoảng 1/3 số giờ. Đổi sang P25/P75 thì lõi cao điểm không đổi (phân tích độ nhạy).

**Dữ liệu thiếu 165 giờ thì xử lý thế nào?**  
Không nội suy hay xóa: chiều Ngày có hours_recorded và is_complete_day; trung bình theo giờ chỉ tính trên giờ có bản ghi. ETL đối chiếu tổng hours_recorded = 17.379.

**Sao biết dữ liệu trong kho đúng?**  
13 phép đối chiếu sau khi nạp, trong đó tổng theo ngày khớp day.csv ở cả 731 ngày (tệp không dùng để nạp). Kiểm thử API so với số tính bằng pandas.

**Tại sao Star mà không Snowflake?**  
Ba chiều chỉ 731, 24, 4 dòng; tách thêm bảng không tiết kiệm đáng kể mà tăng số phép nối.

**Mô hình chỉ bắt 58,5% giờ Cao, vậy có dùng được không?**  
Đó là lý do có hiệu chỉnh mức: dùng sai số 30 ngày gần nhất để kéo dự báo theo xu hướng, bắt được 90% giờ Cao, đổi lại dư chuẩn bị tăng từ 4,4% lên 8,8%. Giới hạn: kiểm định dùng thời tiết thực tế 2012.

**rental_key và instant_id khác nhau thế nào?**  
rental_key là khóa thay thế (surrogate) do kho sinh; instant_id là khóa suy biến (degenerate) giữ mã bản ghi gốc để truy vết về nguồn.
