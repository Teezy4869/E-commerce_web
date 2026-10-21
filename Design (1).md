

**HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG**

**KHOA CÔNG NGHỆ THÔNG TIN 1**

**![][image1]**

**BÁO CÁO**

**PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG** 

**THÔNG TIN** 

		   

| Lớp | : E23TTNT01-B  |
| :---- | :---- |
| **Họ và tên sinh viên** | : **Hoàng Thanh Tùng** |
| **Mã sinh viên**  | : **B23DCVT447** |
| **Giảng viên** | : **PGS.TS.Trần Đình Quế**  |
| **Bài tập** | : **Assignment 1** |

                                                


***Hà Nội – 2026*** 

# **1\. INTRODUCTION**

## **1.1. Assignment Overview**

Assignment 06 xây dựng một prototype hệ thống tìm kiếm sản phẩm thương mại điện tử hỗ trợ nhiều phương thức đầu vào. Hệ thống cho phép khách hàng thực hiện tìm kiếm bằng văn bản, giọng nói và hình ảnh, sau đó chuyển các dạng đầu vào khác nhau về một biểu diễn truy vấn chung để thực hiện retrieval, ranking và trả về kết quả.

Prototype được xây dựng nhằm thể hiện mối quan hệ giữa phân tích yêu cầu, kiến trúc phần mềm ba lớp, mô hình UML và implementation Python. inf\_sys\_analysis\_design\_assignm…

## **1.2. Objectives**

Các mục tiêu chính của hệ thống gồm:

* Phân tích yêu cầu đối với hệ thống tìm kiếm thương mại điện tử.  
* Xác định actor và use case.  
* Thiết kế kiến trúc ba lớp.  
* Xây dựng các mô hình UML.  
* Xây dựng common query representation cho nhiều modality.  
* Triển khai product-search service bằng Python.  
* Triển khai image-similarity search ở mức prototype.  
* Tách biệt retrieval và ranking.  
* Đánh giá prototype trên tập truy vấn thực nghiệm. inf\_sys\_analysis\_design\_assignm…

## **1.3. Scope of the Prototype**

Phạm vi baseline của hệ thống bao gồm:

* Text search.  
* Simulated voice search.  
* Image similarity search.  
* Candidate retrieval.  
* Result ranking.  
* Product repository.  
* Order repository ở mức hỗ trợ use case.  
* Common query representation.  
* Three-layer architecture.

Speech-to-text trong baseline được mô phỏng bằng transcript có sẵn. Image search sử dụng artificial deterministic embedding thay cho real image encoder. Hệ thống sử dụng 12 sản phẩm trong prototype. Design

## **1.4. Report Structure**

Báo cáo được tổ chức thành 11 chương chính:

1. Introduction  
2. Problem Description  
3. Requirements Analysis  
4. Use Case Model  
5. Three-Layer Architecture  
6. UML Sequence Diagram  
7. Python Implementation  
8. Multimodal Search Method  
9. Experimental Results  
10. Discussion  
11. Conclusion

Cấu trúc này bám theo cấu trúc báo cáo được yêu cầu trong Assignment 06\. inf\_sys\_analysis\_design\_assignm…

# **2\. PROBLEM DESCRIPTION**

## **2.1. Problem Statement**

Trong hệ thống thương mại điện tử, khách hàng có thể muốn tìm kiếm sản phẩm thông qua nhiều hình thức khác nhau như nhập từ khóa, sử dụng truy vấn tự nhiên bằng giọng nói hoặc cung cấp hình ảnh của sản phẩm cần tìm.

Hệ thống cần tiếp nhận các dạng input khác nhau và đưa chúng vào một pipeline tìm kiếm thống nhất:

**Different Inputs**

↓

**Common Query Representation**

↓

**Retrieval**

↓

**Ranking**

↓

**Results**

Các truy vấn mẫu bao gồm:

* `black running shoes`  
* `find Nike shoes under 100 dollars`  
* `show me products similar to this image`  
* `find my order 20261001`  
* `where is my latest order?`

inf\_sys\_analysis\_design\_assignm…

## **2.2. E-Commerce Search Context**

Hệ thống quản lý nhóm thông tin cơ bản gồm:

* Product  
* Customer  
* Order  
* OrderItem  
* Product image  
* Product embedding

Product là đối tượng trung tâm của product search. Order được sử dụng để hỗ trợ chức năng tìm kiếm và xem thông tin đơn hàng.

## **2.3. Supported Search Modalities**

| Mode | Input | Processing | Output |
| ----- | ----- | ----- | ----- |
| Text | Keyword / natural-language text | Text processing → Query Representation → Retrieval → Ranking | Ranked products |
| Voice | Audio / transcript | Speech-to-text → Query Representation → Text Retrieval → Ranking | Ranked products |
| Image | Product photograph | Image representation → Similarity Search → Ranking | Ranked products |

Ba modality này là các phương thức tìm kiếm chính của prototype. inf\_sys\_analysis\_design\_assignm…

## **2.4. Search Process**

### **Text Search**

Text Input  
↓  
QueryService  
↓  
Common Query Representation  
↓  
SearchService  
↓  
ProductRepository  
↓  
Candidate Products  
↓  
RankingService  
↓  
Ranked Results

### **Voice Search**

Voice Input  
↓  
VoiceInput  
↓  
SpeechService  
↓  
Transcribed Text  
↓  
QueryService  
↓  
SearchService  
↓  
ProductRepository  
↓  
RankingService  
↓  
Ranked Results

### **Image Search**

Image Input  
↓  
ImageUpload  
↓  
ImageService  
↓  
Artificial Embedding  
↓  
QueryService  
↓  
SearchService  
↓  
VectorIndex  
↓  
Cosine Similarity  
↓  
Candidate Products  
↓  
RankingService  
↓  
Ranked Results

## **2.5. System Scope and Limitations**

Prototype tập trung vào khả năng minh họa kiến trúc và pipeline tìm kiếm thay vì triển khai hệ thống thương mại điện tử production.

Các chức năng không thuộc mandatory baseline gồm:

* Real speech-to-text.  
* Real image encoder.  
* Vector database.  
* Semantic text embedding.  
* Multimodal fusion nâng cao.  
* Personalization.  
* Price-aware ranking.  
* Stock-aware ranking.  
* Web UI. Design

---

# **3\. REQUIREMENTS ANALYSIS**

## **3.1. Actor Analysis**

Hệ thống có một actor chính:

| Actor | Type | Responsibilities |
| ----- | ----- | ----- |
| Customer | Primary Actor | Cung cấp text, voice hoặc image input; tìm kiếm sản phẩm; xem sản phẩm; tìm kiếm đơn hàng; xem đơn hàng |

Không bổ sung Admin, Payment Service, Speech API, Database hoặc AI Model thành external actor trong baseline.

## **3.2. Functional Requirements**

| ID | Functional Requirement | Description | Priority |
| ----- | ----- | ----- | ----- |
| FR-01 | Search Product | Cho phép Customer khởi tạo yêu cầu tìm kiếm sản phẩm | Must |
| FR-02 | Search by Keyword | Nhận text query và thực hiện text-based retrieval | Must |
| FR-03 | Search by Voice | Nhận voice input và chuyển thành text trước khi search | Must |
| FR-04 | Search by Image | Nhận product image và thực hiện similarity search | Must |
| FR-05 | Common Query Representation | Chuyển các modality về query representation chung | Must |
| FR-06 | Retrieve Candidate Products | Truy xuất các product candidates | Must |
| FR-07 | Rank Search Results | Sắp xếp candidate products theo ranking score | Must |
| FR-08 | Display Search Results | Hiển thị sản phẩm và ranking information | Must |
| FR-09 | Search Order | Tìm kiếm thông tin đơn hàng | Required in Use Case Model |
| FR-10 | View Product | Xem thông tin sản phẩm | Must |
| FR-11 | View Order | Xem thông tin đơn hàng | Required in Use Case Model |

Các yêu cầu trên được xây dựng từ specification và architecture baseline trong Design.md. Design

## **3.3. Non-Functional Requirements**

| ID | Non-Functional Requirement | Description | Priority |
| ----- | ----- | ----- | ----- |
| NFR-01 | Layer Separation | Presentation không truy cập trực tiếp Data Layer | Must |
| NFR-02 | Modularity | Tách query, speech, image, search và ranking thành các responsibility riêng | Must |
| NFR-03 | Maintainability | Cho phép thay đổi một component mà ít ảnh hưởng component khác | Must |
| NFR-04 | Extensibility | Có thể thay simulated STT và artificial embedding bằng implementation thực | Should |
| NFR-05 | Usability | Có interaction flow rõ ràng | Should |
| NFR-06 | Testability | Search output và ranking score phải quan sát được | Must |
| NFR-07 | Prototype Performance | Prototype phải thực thi với độ trễ phù hợp cho demonstration | Reasonable Target |

Không đặt SLA số liệu cụ thể cho performance vì assignment không quy định response-time hoặc throughput threshold. Design

## **3.4. Input Modalities**

| Modality | Input | Representation |
| ----- | ----- | ----- |
| Text | Keyword / natural language | `{type: "text", query: ...}` |
| Voice | Transcript sau simulated STT | `{type: "voice", query: ...}` |
| Image | Artificial embedding | `{type: "image", embedding: ...}` |

## **3.5. Search Outputs**

### **Product Search Output**

Kết quả tìm kiếm bao gồm:

* Product.  
* Product name.  
* Relevant product information.  
* Ranking score.  
* Ordered result list.

Các thuộc tính Product gồm:

| Attribute |
| ----- |
| product\_id |
| name |
| category |
| color |
| price |
| stock |
| description |
| image |
| embedding |

### **Order Search Output**

Các thông tin Order gồm:

| Attribute |
| ----- |
| order\_id |
| customer\_id |
| date |
| status |
| total |

## **3.6. Requirements Summary**

Hệ thống cần đảm bảo:

* Một actor chính là Customer.  
* Ba modality tìm kiếm.  
* Common query representation.  
* Candidate retrieval.  
* Ranking.  
* Result presentation.  
* Order Search.  
* View Product.  
* View Order.  
* Three-layer separation.

## **3.7. Requirements Traceability**

| Requirement | Use Case | Component |
| ----- | ----- | ----- |
| FR-01 | UC-01 | SearchUI, SearchService |
| FR-02 | UC-02 | QueryService, SearchService, ProductRepository |
| FR-03 | UC-03 | VoiceInput, SpeechService, QueryService |
| FR-04 | UC-04 | ImageUpload, ImageService, SearchService, VectorIndex |
| FR-05 | UC-02, UC-03, UC-04 | QueryService |
| FR-06 | UC-02, UC-03, UC-04 | SearchService, Repository / VectorIndex |
| FR-07 | UC-02, UC-03, UC-04 | RankingService |
| FR-08 | UC-01, UC-02, UC-03, UC-04 | SearchResultView |
| FR-09 | UC-05 | SearchService, OrderRepository |
| FR-10 | UC-06 | ProductRepository, SearchResultView |
| FR-11 | UC-07 | OrderRepository, SearchResultView |

---

# **4\. USE CASE MODEL**

## **4.1. Use Case Diagram**

### **![][image2]**

**Required Actor:**

* Customer

**Required Use Cases:**

* Search Product  
* Search by Keyword  
* Search by Voice  
* Search by Image  
* Search Order  
* View Product  
* View Order

Assignment yêu cầu Use Case Diagram phải thể hiện Customer và bảy use case trên. inf\_sys\_analysis\_design\_assignm…

## **4.2. Actor Description**

| Actor | Description |
| ----- | ----- |
| Customer | Người sử dụng hệ thống để tìm kiếm sản phẩm, tìm kiếm đơn hàng và xem thông tin tương ứng |

## **4.3. Use Case Catalogue**

| ID | Use Case | Actor | Goal | Main Outcome |
| ----- | ----- | ----- | ----- | ----- |
| UC-01 | Search Product | Customer | Tìm kiếm sản phẩm | Ranked product results |
| UC-02 | Search by Keyword | Customer | Tìm bằng text | Text-based results |
| UC-03 | Search by Voice | Customer | Tìm bằng voice | Transcribed and ranked results |
| UC-04 | Search by Image | Customer | Tìm sản phẩm tương tự hình ảnh | Similar-product results |
| UC-05 | Search Order | Customer | Tìm đơn hàng | Order information |
| UC-06 | View Product | Customer | Xem sản phẩm | Product information |
| UC-07 | View Order | Customer | Xem đơn hàng | Order information |

## **4.4. Use Case Relationships**

Các modality-specific use case là các dạng cụ thể của Search Product:

* Search by Keyword → Search Product  
* Search by Voice → Search Product  
* Search by Image → Search Product

Search Order, View Product và View Order được giữ độc lập trong use case model.

# **5\. THREE-LAYER ARCHITECTURE**

## **5.1. Architecture Overview**

Hệ thống sử dụng ba layer:

1. Presentation Layer.  
2. Application / Intelligence Layer.  
3. Data Layer.

Đây là kiến trúc được quy định trực tiếp trong assignment. inf\_sys\_analysis\_design\_assignm…

### **![][image3]**

## **5.2. Presentation Layer**

### **Components**

* SearchUI  
* VoiceInput  
* ImageUpload  
* SearchResultView

### **Responsibilities**

**SearchUI**

* Tiếp nhận yêu cầu tìm kiếm.  
* Điều phối interaction flow.  
* Không truy cập database trực tiếp.

**VoiceInput**

* Tiếp nhận voice input.  
* Chuyển input đến SpeechService.

**ImageUpload**

* Tiếp nhận product image.  
* Chuyển image sang ImageService.

**SearchResultView**

* Hiển thị returned products.  
* Hiển thị ranking scores.  
* Hiển thị thông tin kết quả.

## **5.3. Application / Intelligence Layer**

### **Components**

* QueryService  
* SpeechService  
* ImageService  
* SearchService  
* RankingService

### **QueryService**

Chuyển các modality-specific input thành common query representation.

### **SpeechService**

Thực hiện speech-to-text ở mức prototype.

Baseline:

audio\_input  
    ↓  
transcribed text

Speech recognition được simulated.

### **ImageService**

Tạo image representation cho image search.

Baseline sử dụng artificial deterministic embedding.

### **SearchService**

Thực hiện candidate retrieval.

SearchService không chịu trách nhiệm ordering cuối cùng của result list.

### **RankingService**

Nhận candidates và thực hiện ranking.

Retrieval và ranking được tách biệt thành hai responsibility độc lập.

## **5.4. Data Layer**

### **Components**

* ProductRepository  
* OrderRepository  
* VectorIndex  
* ProductDatabase  
* OrderDatabase  
* ImageStorage

### **ProductRepository**

Cung cấp dữ liệu Product.

### **OrderRepository**

Cung cấp dữ liệu Order.

### **VectorIndex**

Cung cấp product embeddings cho image similarity search.

### **ProductDatabase**

Lưu product dataset.

### **OrderDatabase**

Lưu order dataset.

### **ImageStorage**

Lưu sample/product images.

## **5.5. Layer Responsibilities**

| Layer | Main Responsibility |
| ----- | ----- |
| Presentation | Collect input and display results |
| Application / Intelligence | Query conversion, retrieval, image processing, speech handling, ranking |
| Data | Product data, order data, image data, vector representations |

## **5.6. Component Architecture**

### **Presentation**

| Component |
| ----- |
| SearchUI |
| VoiceInput |
| ImageUpload |
| SearchResultView |

### **Application / Intelligence**

| Component |
| ----- |
| QueryService |
| SpeechService |
| ImageService |
| SearchService |
| RankingService |

### **Data**

| Component |
| ----- |
| ProductRepository |
| OrderRepository |
| VectorIndex |
| ProductDatabase |
| OrderDatabase |
| ImageStorage |

## **5.7. Inter-Layer Dependencies**

Dependency direction:

Presentation  
      ↓  
Application / Intelligence  
      ↓  
Data

Không tồn tại dependency trực tiếp:

Presentation → Data

Implementation cuối cùng cũng giữ nguyên nguyên tắc này. Design

## **5.8. Architecture Design Principles**

### **Principle 1: Separate UI from Business Logic**

Presentation không truy cập trực tiếp database.

### **Principle 2: Different Inputs, Common Representation**

Text, voice và image được chuyển về representation mà retrieval system có thể xử lý.

### **Principle 3: Retrieval and Ranking Are Different**

Retrieval tạo candidate set.

Ranking sắp xếp candidate set.

### **Principle 4: Start Simple**

Prototype sử dụng keyword matching và artificial embedding trước khi xem xét các AI component nâng cao.

# **6\. UML SEQUENCE DIAGRAMS**

## **6.1. Voice Search**

Figure 6.1 shows the voice-search scenario. `SearchUI` is the boundary, the services are controls, and `Product` is the entity. The audio is converted to text first, and the request is then handled as a text query. `SearchService` retrieves candidate products, and `RankingService` subsequently orders the candidates. Design

### **Figure 6.1. Sequence diagram of voice search**

**![][image4]**

### **Table 6.1. Messages of the voice search**

| Step | From → To | Message | Data Passed |
| ----- | ----- | ----- | ----- |
| 1 | Customer → SearchUI | `provideVoiceInput(audio)` | Recorded audio |
| 2 | SearchUI → SpeechService | `transcribe(audio)` | Audio |
| 3 | SpeechService → SearchUI | `transcript` | Recognised text |
| 4 | SearchUI → QueryService | `voice_query(transcript)` | Query object: type, tokens, weights |
| 5 | SearchUI → SearchService | `retrieve(query)` | Query object |
| 6 | SearchService → Product | `get_products()` | Product records |
| 7 | SearchUI → RankingService | `rank(candidates, query)` | Candidates with raw scores |
| 8 | SearchUI → Customer | `show_results(ranked_list)` | Ranked products with scores |

### **Table 6.2. Design decisions in the voice sequence**

| Decision | Options | Choice | Reason |
| ----- | ----- | ----- | ----- |
| Participants | Boundary, control and entity stereotypes, or untyped objects | **Stereotypes** | They show the interaction boundary, processing logic and data entity. `SearchUI` handles customer interaction, the services hold the processing logic, and `Product` represents product data. |
| Orchestration | `SearchUI` calls each service, or a controller between them | **SearchUI calls each service** | A separate controller would add another participant that is not required by the assignment. The interface directly coordinates the listed services. |
| Retrieval and ranking | One step, or two | **Two steps** | `SearchService` retrieves candidates with raw scores. `RankingService` then applies the ranking rule, allowing retrieval and ranking to remain separate responsibilities. |
| Communication | Asynchronous or synchronous | **Synchronous** | The transcript is required before the query can be constructed, so the interface waits for the speech-processing result before continuing. |
| Speech model | Explicit participant or internal service implementation | **Internal to SpeechService** | The speech model itself is not modeled as a separate participant, allowing the speech implementation to be replaced without changing the sequence structure. |

## **6.2. Text, Image and Multimodal Search**

Text search follows the same sequence as voice search without the speech-processing step. Image search replaces the speech-processing stage with image encoding. `SearchService` retrieves candidate products through `VectorIndex`, while the corresponding `Product` entities provide the product records.

### **Figure 6.2. Sequence diagram of text search**

**![][image5]**

### **Figure 6.3. Sequence diagram of image search**

**![][image6]**

In image search, the query image is encoded directly into an image representation. `SearchService` uses `VectorIndex` to identify the closest products, after which the product records are loaded for the returned candidates. `ImageStorage` does not participate directly in the query sequence because the query image is encoded before retrieval and the catalogue images have already been represented in the vector index.

### **Figure 6.4. Sequence diagram of multimodal search**

**![][image7]**

In multimodal search, the query object contains the text representation, image vector and corresponding weights. `RankingService` combines the scores produced by the individual retrieval mechanisms to obtain the final ranked result list.

### **Table 6.3. Sequence participants by search modality**

| Search Mode | Main Participants | Processing |
| ----- | ----- | ----- |
| Text | Customer, SearchUI, QueryService, SearchService, Product, RankingService | Text query → Retrieval → Ranking |
| Voice | Customer, SearchUI, SpeechService, QueryService, SearchService, Product, RankingService | Speech-to-text → Text query → Retrieval → Ranking |
| Image | Customer, SearchUI, ImageService, QueryService, SearchService, VectorIndex, Product, RankingService | Image encoding → Vector retrieval → Ranking |
| Multimodal | Customer, SearchUI, QueryService, SearchService, VectorIndex, Product, RankingService | Text \+ image representations → Combined retrieval → Ranking |

# **7\. PYTHON IMPLEMENTATION**

## **7.1. Implementation Overview**

Python prototype được xây dựng để phản ánh trực tiếp architecture đã thiết kế trong UML.

Implementation hiện tại hỗ trợ:

* Product repository.  
* Text search.  
* Simulated voice search.  
* Image similarity search.  
* Result ranking.  
* Order search.  
* Test suite.  
* Demonstration flow.

Implementation thực tế đã được chạy và validation đạt 24/24 automated tests. Design

## **7.2. Project Directory Structure**

assignment06/  
│  
├── main.py  
│  
├── presentation/  
│   ├── \_\_init\_\_.py  
│   ├── search\_ui.py  
│   ├── voice\_input.py  
│   ├── image\_upload.py  
│   └── search\_result\_view.py  
│  
├── application/  
│   ├── \_\_init\_\_.py  
│   ├── query\_service.py  
│   ├── speech\_service.py  
│   ├── image\_service.py  
│   ├── search\_service.py  
│   └── ranking\_service.py  
│  
├── data/  
│   ├── \_\_init\_\_.py  
│   ├── product\_repository.py  
│   ├── order\_repository.py  
│   └── vector\_index.py  
│  
├── dataset/  
│   ├── products.json  
│   └── orders.json  
│  
├── images/  
│   ├── product\_01.jpg  
│   ├── product\_02.jpg  
│   ├── ...  
│   ├── query\_shoes.jpg  
│   ├── query\_bag.jpg  
│   └── query\_watch.jpg  
│  
├── tests/  
│   ├── test\_text\_search.py  
│   ├── test\_voice\_search.py  
│   ├── test\_image\_search.py  
│   └── test\_ranking.py  
│  
└── README.md

## **7.3. Product Repository**

Prototype sử dụng 12 sản phẩm, đáp ứng yêu cầu tối thiểu 10 products.

Product schema:

product\_id  
name  
category  
color  
price  
stock  
description  
image  
embedding

ProductRepository cung cấp dữ liệu cho Application Layer.

## **7.4. Query Service**

### **Text Query**

{  
    "type": "text",  
    "query": "black running shoes"  
}

### **Voice Query**

{  
    "type": "voice",  
    "query": "find black running shoes"  
}

### **Image Query**

{  
    "type": "image",  
    "embedding": \[...\]  
}

QueryService cung cấp common interface cho nhiều modality.

## **7.5. Text Search**

Text retrieval kiểm tra từ khóa trong:

* name  
* category  
* color  
* description

Ví dụ:

Query: black shoes

Hệ thống tạo candidate set từ product collection.

Sau đó:

SearchService  
      ↓  
Candidate Products  
      ↓  
RankingService  
      ↓  
Ordered Results

Demo thực tế với `black shoes` tạo ra 7 candidates và sản phẩm đứng đầu là `Nike Running Shoes` với score 2\. Design

### **\[CHÈN HÌNH 7.1: SCREENSHOT TERMINAL E-01 \- TEXT SEARCH\]**

## **7.6. Voice Search**

Voice search sử dụng simulated speech-to-text.

Input:

find running shoes

Transcription:

find running shoes

Query representation:

{  
    "type": "voice",  
    "query": "find running shoes"  
}

Kết quả thực tế:

* 5 candidates.  
* Nike Running Shoes: score 2\.  
* Adidas Running Shoes: score 2\.  
* Top-1: Nike Running Shoes.

Design

### **\[CHÈN HÌNH 7.2: SCREENSHOT TERMINAL E-02 \- VOICE SEARCH\]**

## **7.7. Image Similarity Search**

Image demo sử dụng:

images/query\_shoes.jpg

ImageService ánh xạ image này tới deterministic embedding:

\[0.88, 0.12, 0.22\]

Similarity được tính bằng cosine similarity.

Top results thực tế:

| Rank | Product | Similarity |
| ----- | ----- | ----- |
| 1 | Nike Running Shoes | 0.9994 |
| 2 | Adidas Running Shoes | 0.9985 |
| 3 | Blue Sports Shoes | 0.9943 |
| 4 | Green Hiking Shoes | 0.9771 |
| 5 | White Casual Sneakers | 0.9645 |

Design

### **\[CHÈN HÌNH 7.3: SCREENSHOT TERMINAL E-03 \- IMAGE SEARCH\]**

## **7.8. Result Ranking**

RankingService thực hiện ordering sau retrieval.

### **Text Ranking**

text\_score \=  
number of query terms found  
in searchable product text

### **Image Ranking**

similarity(q, p)  
\=  
(q · p) / (||q|| ||p||)

Higher score corresponds to a higher result position.

## **7.9. Main Program**

Prototype được khởi chạy bằng:

cd assignment06  
python main.py

Main program thực hiện demonstration cho:

1. Text search.  
2. Voice search.  
3. Image search.  
4. Order search.

## **7.10. Implementation Validation**

### **\[CHÈN HÌNH 7.4: SCREENSHOT TERMINAL E-07 \- FULL TEST SUITE\]**

| Test Category | Result |
| ----- | ----- |
| Python compileall | PASS |
| Text tests | 5/5 |
| Voice tests | 4/4 |
| Image tests | 7/7 |
| Ranking tests | 5/5 |
| Integration tests | 3/3 |
| **Total** | **24/24 PASS** |

`main.py` cũng chạy thành công với cả ba search modes và Order Search. Design

---

# **8\. MULTIMODAL SEARCH METHOD**

## **8.1. Multimodal Search Overview**

Hệ thống sử dụng kiến trúc thống nhất cho nhiều dạng input:

Text ───────────┐  
                │  
Voice → Speech ─┼──→ Common Query Representation  
                │  
Image → Encoder ┘  
                         ↓  
                    Retrieval  
                         ↓  
                      Ranking  
                         ↓  
                      Results

## **8.2. Common Query Representation**

Common query representation là trung tâm của multimodal search pipeline.

### **Text**

{  
    "type": "text",  
    "query": "black shoes"  
}

### **Voice**

{  
    "type": "voice",  
    "query": "find running shoes"  
}

### **Image**

{  
    "type": "image",  
    "embedding": \[0.88, 0.12, 0.22\]  
}

## **8.3. Text Query Processing**

Text Input  
↓  
QueryService  
↓  
Text Query Representation  
↓  
SearchService  
↓  
ProductRepository  
↓  
Candidates  
↓  
RankingService  
↓  
Results

## **8.4. Voice Query Processing**

Voice Input  
↓  
VoiceInput  
↓  
SpeechService  
↓  
Transcribed Text  
↓  
QueryService  
↓  
Voice Query Representation  
↓  
SearchService  
↓  
Candidates  
↓  
RankingService  
↓  
Results

## **8.5. Image Query Processing**

Image  
↓  
ImageUpload  
↓  
ImageService  
↓  
Artificial Embedding  
↓  
QueryService  
↓  
Image Query Representation  
↓  
SearchService  
↓  
VectorIndex  
↓  
Cosine Similarity  
↓  
Candidates  
↓  
RankingService  
↓  
Results

## **8.6. Candidate Retrieval**

Text retrieval sử dụng keyword matching.

Image retrieval sử dụng vector similarity.

Retrieval chỉ tạo candidate set và không thực hiện final ordering.

## **8.7. Similarity Calculation**

Cosine similarity:

\\\[ Similarity(q,p) \= \\frac{q\\cdot p}{\\|q\\|\\|p\\|} \\\]

Giá trị similarity càng lớn thì sản phẩm càng gần query embedding trong feature space.

## **8.8. Ranking Mechanism**

RankingService nhận candidate products:

Candidate 1 → Score  
Candidate 2 → Score  
Candidate 3 → Score  
...

Sau đó:

Highest Score  
      ↓  
...  
Lowest Score

## **8.9. Multimodal Query Fusion**

Baseline hiện tại không triển khai multimodal fusion nâng cao.

Các modality được xử lý thông qua common query representation, sau đó đi vào retrieval pipeline tương ứng.

## **8.10. Search Pipeline**

Pipeline thực tế cuối cùng:

Different Inputs  
        ↓  
Common Query Representation  
        ↓  
SearchService  
        ↓  
Candidate Retrieval  
        ↓  
RankingService  
        ↓  
Ranked Results  
        ↓  
SearchResultView

Kiến trúc thực tế sau integration tiếp tục giữ nguyên nguyên tắc này. Design

---

# **9\. EXPERIMENTAL RESULTS**

## **9.1. Evaluation Objective**

Evaluation kiểm tra toàn bộ pipeline:

Input  
↓  
Query Representation  
↓  
Retrieval  
↓  
Ranking  
↓  
Results

Các modality được đánh giá:

* Text search.  
* Simulated voice search.  
* Image similarity search.  
* Result ranking. Design

## **9.2. Test Dataset**

Tổng số evaluation queries:

* 9 Text.  
* 9 Voice.  
* 3 Image.

Tổng cộng:

$21\ queries$

### **Image Queries**

* `images/query_shoes.jpg`  
* `images/query_bag.jpg`  
* `images/query_watch.jpg`

### **Test Cases**

| Test ID | Mode | Input | Expected Result |
| ----- | ----- | ----- | ----- |
| T01 | Text | `black shoes` | Nike Running Shoes |
| T02 | Text | `running shoes` | Nike Running Shoes |
| T03 | Text | `black leather bag` | Black Leather Bag |
| T04 | Text | `red bag` | Red Canvas Bag |
| T05 | Text | `gold watch` | Gold Classic Watch |
| T06 | Text | `blue jacket` | Blue Denim Jacket |
| T07 | Text | `green hiking shoes` | Green Hiking Shoes |
| T08 | Text | `laptop` | No matching product |
| T09 | Text | `silver digital watch` | Silver Digital Watch |
| V01 | Voice | `find black shoes` | Nike Running Shoes |
| V02 | Voice | `show running shoes` | Nike Running Shoes |
| V03 | Voice | `search black leather bag` | Black Leather Bag |
| V04 | Voice | `find red bag` | Red Canvas Bag |
| V05 | Voice | `show gold watch` | Gold Classic Watch |
| V06 | Voice | `find blue jacket` | Blue Denim Jacket |
| V07 | Voice | `find green hiking shoes` | Green Hiking Shoes |
| V08 | Voice | `find laptop` | No matching product |
| V09 | Voice | `find silver digital watch` | Silver Digital Watch |
| I01 | Image | `query_shoes.jpg` | Nike Running Shoes |
| I02 | Image | `query_bag.jpg` | Black Leather Bag |
| I03 | Image | `query_watch.jpg` | Silver Digital Watch |

Design

## **9.3. Execution Results**

| ID | Mode | Input | Expected | Top-1 Result | Score | Success |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| T01 | Text | `black shoes` | Nike Running Shoes | Nike Running Shoes | 2 | Yes |
| T02 | Text | `running shoes` | Nike Running Shoes | Nike Running Shoes | 2 | Yes |
| T03 | Text | `black leather bag` | Black Leather Bag | Black Leather Bag | 3 | Yes |
| T04 | Text | `red bag` | Red Canvas Bag | Red Canvas Bag | 2 | Yes |
| T05 | Text | `gold watch` | Gold Classic Watch | Gold Classic Watch | 2 | Yes |
| T06 | Text | `blue jacket` | Blue Denim Jacket | Blue Denim Jacket | 2 | Yes |
| T07 | Text | `green hiking shoes` | Green Hiking Shoes | Green Hiking Shoes | 3 | Yes |
| T08 | Text | `laptop` | No matching product | No matching product | N/A | Yes |
| T09 | Text | `silver digital watch` | Silver Digital Watch | Silver Digital Watch | 3 | Yes |
| V01 | Voice | `find black shoes` | Nike Running Shoes | Nike Running Shoes | 2 | Yes |
| V02 | Voice | `show running shoes` | Nike Running Shoes | Nike Running Shoes | 2 | Yes |
| V03 | Voice | `search black leather bag` | Black Leather Bag | Black Leather Bag | 3 | Yes |
| V04 | Voice | `find red bag` | Red Canvas Bag | Red Canvas Bag | 2 | Yes |
| V05 | Voice | `show gold watch` | Gold Classic Watch | Gold Classic Watch | 2 | Yes |
| V06 | Voice | `find blue jacket` | Blue Denim Jacket | Blue Denim Jacket | 2 | Yes |
| V07 | Voice | `find green hiking shoes` | Green Hiking Shoes | Green Hiking Shoes | 3 | Yes |
| V08 | Voice | `find laptop` | No matching product | No matching product | N/A | Yes |
| V09 | Voice | `find silver digital watch` | Silver Digital Watch | Silver Digital Watch | 3 | Yes |
| I01 | Image | `query_shoes.jpg` | Nike Running Shoes | Nike Running Shoes | 0.9994 | Yes |
| I02 | Image | `query_bag.jpg` | Black Leather Bag | Black Leather Bag | 0.9994 | Yes |
| I03 | Image | `query_watch.jpg` | Silver Digital Watch | Silver Digital Watch | 0.9992 | Yes |

Design

## **9.4. Success Rate**

\\\[ Success\\ Rate \= \\frac{Successful\\ Queries}{Total\\ Queries}\\times100\\% \\\]\\\[ \= \\frac{21}{21}\\times100\\% \= 100.0\\% \\\]

| Metric | Result |
| ----- | ----- |
| Total queries | 21 |
| Successful queries | 21 |
| Failed queries | 0 |
| Success rate | 100.0% |

### **Per-Modality Result**

| Mode | Queries | Successful | Failed | Success Rate |
| ----- | ----- | ----- | ----- | ----- |
| Text | 9 | 9 | 0 | 100.0% |
| Voice | 9 | 9 | 0 | 100.0% |
| Image | 3 | 3 | 0 | 100.0% |
| **Total** | **21** | **21** | **0** | **100.0%** |

Design

## **9.5. Text Search Results**

Text Search:

$9/9\ successful$

Các truy vấn:

* `black shoes`  
* `black leather bag`  
* `green hiking shoes`  
* `silver digital watch`

Các truy vấn đều trả về expected product ở Top-1.

Điểm số cao nhất quan sát được:

$3$

đối với:

* `black leather bag`  
* `green hiking shoes`  
* `silver digital watch`

## **9.6. Voice Search Results**

Voice Search:

$9/9\ successful$

Pipeline:

Voice Input  
↓  
Simulated Transcription  
↓  
Voice Query Representation  
↓  
SearchService  
↓  
RankingService  
↓  
Results

Evaluation này đánh giá thành công của voice-search pipeline sau transcript, không đánh giá chất lượng speech recognition thực tế. Design

## **9.7. Image Search Results**

| Query Image | Top-1 Product | Similarity |
| ----- | ----- | ----- |
| `query_shoes.jpg` | Nike Running Shoes | 0.9994 |
| `query_bag.jpg` | Black Leather Bag | 0.9994 |
| `query_watch.jpg` | Silver Digital Watch | 0.9992 |

Mean Top-1 similarity:

$\frac{0.9994+0.9994+0.9992}{3}=0.9993$

Giá trị này là cosine similarity trong artificial feature space, không phải visual-recognition accuracy. Design

## **9.8. Ranking Results**

RankingService đảm bảo candidate results được sắp xếp theo score giảm dần.

Ví dụ image query `query_shoes.jpg`:

| Rank | Product | Score |
| ----- | ----- | ----- |
| 1 | Nike Running Shoes | 0.9994 |
| 2 | Adidas Running Shoes | 0.9985 |
| 3 | Blue Sports Shoes | 0.9943 |
| 4 | Green Hiking Shoes | 0.9771 |
| 5 | White Casual Sneakers | 0.9645 |

## **9.9. Incorrect Results**

Không có failed case trong 21-query evaluation set.

Tuy nhiên, evaluation phát hiện tie case:

Nike Running Shoes      score \= 2  
Adidas Running Shoes    score \= 2

Trong trường hợp bằng điểm, thứ tự hiện tại giữ nguyên candidate ordering. Design

## **9.10. Automated Test Validation**

Ngoài 21 evaluation queries, automated test suite đạt:

$24/24\ PASS$

| Test Category | Result |
| ----- | ----- |
| Compile | PASS |
| Text Tests | 5/5 |
| Voice Tests | 4/4 |
| Image Tests | 7/7 |
| Ranking Tests | 5/5 |
| Integration Tests | 3/3 |
| **Total** | **24/24 PASS** |

21-query experimental evaluation và 24-case software test suite là hai tập kiểm thử khác nhau. Design

### **\[CHÈN HÌNH 9.1: SCREENSHOT E-07 \- TEST SUITE 24/24 PASS\]**

---

# **10\. DISCUSSION**

## **10.1. System Performance**

Prototype thực thi thành công toàn bộ pipeline và automated test suite.

Validation:

$24/24\ tests\ PASS$

Ba search modalities đều thực hiện thành công trong demonstration.

## **10.2. Search Quality**

### **Text Search**

Text Search đạt 9/9 successful trên tập query được xây dựng từ các thuộc tính hiện có trong catalog.

### **Voice Search**

Voice Search đạt 9/9 successful sau simulated transcription.

### **Image Search**

Image Search đạt 3/3 successful với Top-1 similarity cao.

## **10.3. Comparison Between Search Modalities**

| Aspect | Text | Voice | Image |
| ----- | ----- | ----- | ----- |
| Input | Text | Transcript | Image |
| Pre-processing | Query normalization | Simulated STT | Artificial embedding |
| Retrieval | Keyword | Keyword after STT | Vector similarity |
| Ranking | Score | Score | Cosine similarity |
| Evaluation | 9/9 | 9/9 | 3/3 |
| Baseline limitation | Keyword-based | No real STT | Artificial embedding |

## **10.4. Strengths of the Prototype**

### **Architecture Separation**

Ba layer được tách biệt rõ ràng:

Presentation  
↓  
Application / Intelligence  
↓  
Data

### **Common Query Representation**

Các modality khác nhau có thể đi vào một search pipeline thống nhất.

### **Retrieval / Ranking Separation**

SearchService thực hiện retrieval.

RankingService thực hiện ranking.

### **Deterministic Image Processing**

Artificial image embeddings được xác định trước, giúp kết quả reproducible.

## **10.5. Limitations**

### **Small Dataset**

Prototype có 12 products.

100% success rate trên 21 queries trong catalog nhỏ không đại diện cho large-scale search quality.

### **Keyword Retrieval**

Text search chưa hỗ trợ:

* Semantic retrieval.  
* Synonym expansion.  
* Spell correction.  
* Natural-language constraint extraction.

### **Simulated Speech Recognition**

Không đánh giá:

* Speech recognition accuracy.  
* Accent robustness.  
* Noise robustness.  
* Transcription errors.

### **Artificial Image Embeddings**

Không sử dụng:

* CNN.  
* CLIP.  
* Vision Transformer.  
* Real image encoder.

### **Simplistic Ranking**

Ranking chưa sử dụng:

* Learned relevance.  
* Personalization.  
* Popularity.  
* Price preference.  
* Stock-aware ranking.

Các hạn chế trên được ghi nhận trong evaluation của implementation hiện tại. Design

## **10.6. Implementation Challenges**

### **Retrieval và Ranking bị chồng lấn**

Ban đầu SearchService vừa retrieval vừa sort results.

Sau integration:

SearchService  
↓  
Candidate Products  
↓  
RankingService  
↓  
Ordered Results

### **Dependency Ngược trong UML**

Component diagram trước đây có dependency:

SearchService → SearchResultView  
RankingService → SearchResultView

Dependency này đã được loại bỏ để giữ kiến trúc:

Presentation  
↓  
Application  
↓  
Data

### **Documentation Count**

Số test được cập nhật từ 21 lên 24 sau khi bổ sung integration tests.

### **Deterministic Image Processing**

Image processing được chuyển sang deterministic embedding nhằm bảo đảm khả năng reproducibility. Design

## **10.7. Possible Improvements**

Các hướng mở rộng phù hợp với prototype gồm:

* Real speech-to-text.  
* Real image embedding.  
* Semantic text embedding.  
* Vector database.  
* Multimodal fusion.  
* Price filtering.  
* Category filtering.  
* Stock-aware ranking.  
* Web-based UI.

## **10.8. Future Extensions**

Pipeline mở rộng có thể phát triển thành:

Text  
  ───────┐  
         │  
Voice ───┼──→ Multimodal Query  
         │  
Image ───┘  
             ↓  
      Candidate Retrieval  
             ↓  
      Filtering / Ranking  
             ↓  
          Top-k Products

Các extension này thuộc nhóm advanced work thay vì mandatory baseline. inf\_sys\_analysis\_design\_assignm…

---

# **11\. CONCLUSION**

## **11.1. Summary of the Implemented System**

Assignment 06 đã triển khai một prototype Multimodal Search System cho e-commerce với ba phương thức:

* Text Search.  
* Voice Search.  
* Image Search.

Ba modality được chuyển về common query representation trước khi thực hiện retrieval, ranking và result presentation.

## **11.2. Requirements Fulfillment**

Prototype đáp ứng các thành phần chính của assignment:

| Requirement | Status |
| ----- | ----- |
| Product Repository | Implemented |
| Text Search | Implemented |
| Simulated Voice Search | Implemented |
| Image Similarity Search | Implemented |
| Result Ranking | Implemented |
| Common Query Representation | Implemented |
| Three-Layer Architecture | Implemented |
| Use Case Model | Completed |
| Voice Sequence Diagram | Completed |
| Three mandatory demonstrations | Completed |
| Product Dataset ≥ 10 | 12 products |
| Experimental Evaluation | Completed |

Design

## **11.3. UML and Architecture Outcomes**

Hệ thống được mô hình hóa bằng:

* Use Case Diagram.  
* Three-Layer Component Diagram.  
* Voice Search Sequence Diagram.

### **\[CHÈN HÌNH 11.1: USE CASE DIAGRAM\]**

### **\[CHÈN HÌNH 11.2: THREE-LAYER COMPONENT DIAGRAM\]**

### **\[CHÈN HÌNH 11.3: VOICE SEARCH SEQUENCE DIAGRAM\]**

Các mô hình UML và Python implementation được duy trì nhất quán thông qua mapping:

Requirements  
↓  
Use Cases  
↓  
UML Components  
↓  
Python Modules  
↓  
Tests

## **11.4. Prototype Evaluation Summary**

Kết quả evaluation:

$21/21\ successful$  
\\\[ Success\\ Rate \= 100.0\\% \\\]

| Mode | Success Rate |
| ----- | ----- |
| Text | 100.0% |
| Voice | 100.0% |
| Image | 100.0% |
| **Overall** | **100.0%** |

Automated validation:

$24/24\ PASS$

Kết quả này chỉ phản ánh tập test nhỏ và deterministic của prototype, không đại diện cho production-scale search accuracy. Design

## **11.5. Future Development**

Hệ thống có thể tiếp tục phát triển theo hướng:

Keyword Search  
      ↓  
Semantic Search  
      ↓  
Embedding Search  
      ↓  
Multimodal Retrieval  
      ↓  
Advanced Ranking

Mục tiêu phát triển tiếp theo là thay thế các thành phần mô phỏng bằng các AI component thực tế trong khi vẫn giữ nguyên kiến trúc ba lớp và nguyên tắc phân tách retrieval và ranking.

---

# **PHỤ LỤC**

## **APPENDIX A. VISUAL PARADIGM DIAGRAMS**

### **A.1. Use Case Diagram**

**\[CHÈN ẢNH USE CASE DIAGRAM TỪ VISUAL PARADIGM\]**

### **A.2. Three-Layer Component Diagram**

**\[CHÈN ẢNH COMPONENT DIAGRAM TỪ VISUAL PARADIGM\]**

### **A.3. Voice Search Sequence Diagram**

**\[CHÈN ẢNH SEQUENCE DIAGRAM TỪ VISUAL PARADIGM\]**

---

## **APPENDIX B. PYTHON IMPLEMENTATION EVIDENCE**

### **B.1. Text Search**

**\[CHÈN SCREENSHOT E-01\]**

### **B.2. Voice Search**

**\[CHÈN SCREENSHOT E-02\]**

### **B.3. Image Search**

**\[CHÈN SCREENSHOT E-03\]**

### **B.4. Full Test Suite**

**\[CHÈN SCREENSHOT E-07\]**

---

## **APPENDIX C. DATASET**

### **C.1. Product Dataset**

**\[CHÈN BẢNG / SCREENSHOT PRODUCT DATASET\]**

### **C.2. Order Dataset**

**\[CHÈN BẢNG / SCREENSHOT ORDER DATASET\]**

### **C.3. Sample Images**

**\[CHÈN CÁC SAMPLE IMAGE ĐƯỢC SỬ DỤNG\]**

---

## **APPENDIX D. DEMONSTRATION RESULTS**

### **D.1. Text Search Demonstration**

Query:  
black shoes

Top Result:  
Nike Running Shoes

Score:  
2

### **D.2. Voice Search Demonstration**

Voice Input:  
find running shoes

Transcription:  
find running shoes

Top Result:  
Nike Running Shoes

Score:  
2

### **D.3. Image Search Demonstration**

Query:  
images/query\_shoes.jpg

Top Result:  
Nike Running Shoes

Similarity:  
0.9994

### **D.4. Additional Order Demonstration**

Order Search  
↓  
OrderRepository  
↓  
Order Information  
---

## **APPENDIX E. EVIDENCE INDEX**

| Evidence ID | Evidence |
| ----- | ----- |
| E-01 | Text Search terminal |
| E-02 | Voice Search terminal |
| E-03 | Image Search terminal |
| E-04 | Visual Paradigm Use Case Diagram |
| E-05 | Visual Paradigm Three-Layer Component Diagram |
| E-06 | Visual Paradigm Voice Sequence Diagram |
| E-07 | Automated Test Suite 24/24 PASS |

Design

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,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>

[image5]: <data:image/png;base64,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>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,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>