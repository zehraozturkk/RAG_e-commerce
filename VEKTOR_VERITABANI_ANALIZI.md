# Vektör Veritabanı Analizi — RAG E-Ticaret Projesi

Bu belge, projede **Pinecone** vektör veritabanının nasıl kullanıldığını adım adım açıklamaktadır.

---

## 1. Kullanılan Vektör Veritabanı

**Pinecone** — bulut tabanlı, yönetilen (serverless) bir vektör veritabanıdır.

| Parametre | Değer |
|-----------|-------|
| İndeks Adı | `ecommerce-2` |
| Vektör Boyutu | `384` (embedding modeliyle eşleşir) |
| Bulut / Bölge | AWS / `us-east-1` |
| Namespace (yükleme) | `e-commerce` veya `ecommerce-22` |
| Namespace (sorgulama) | `e-commerce2` veya `ecommerce-22` |

---

## 2. Genel Mimari

```
PostgreSQL ──► Embedding Oluşturma ──► Pinecone (Yükleme)
                                              │
Kullanıcı Sorusu ──► Embedding ──► Pinecone (Benzerlik Arama)
                                              │
                               Bağlam (Context) + Soru
                                              │
                                        GPT-4 (LLM)
                                              │
                                        Yanıt (Cevap)
```

---

## 3. Vektör İndeksinin Oluşturulması

**Dosya:** `postgre_to_pinecone.py` — `upload_to_pinecone()` metodu

```python
pc = Pinecone(api_key=pinecone_api_key)
index_name = "ecommerce-2"

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=384,          # Embedding modelinin çıktı boyutu
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
```

İndeks yoksa otomatik oluşturulur; zaten varsa mevcut indeks kullanılır.

---

## 4. Veri Kaynağı ve Vektöre Dönüştürme

### 4.1 PostgreSQL'den Veri Çekme

**Dosya:** `postgre_to_pinecone.py` — `fetch_data_from_postgres()` metodu

`orders`, `users` ve `products` tabloları JOIN'lenerek her sipariş için kullanıcı ve ürün bilgileri birleştirilir:

```sql
SELECT
    u.user_id, u.user_name,
    o.order_id, o.product_id, o.order_date,
    p.product_name, p.category
FROM orders o
JOIN users u ON o.user_id = u.user_id
JOIN products p ON o.product_id = p.product_id
ORDER BY o.order_date DESC;
```

### 4.2 Metin Oluşturma ve Embedding

**Dosya:** `postgre_to_pinecone.py` — `create_embeddings()` metodu

Her kullanıcı-tarih kombinasyonu bir **doğal dil cümlesi**ne dönüştürülür:

```python
text = f"User {user_name} ordered {products_text} on {order_date}"
# Örnek: "User Alice Brown ordered Shampoo (Personal Care) and Body Lotion (Personal Care) on 2024-03-10"

embedding = self.model.encode(text)  # 384 boyutlu vektör üretir
```

Kullanılan embedding modeli: **`all-MiniLM-L12-v2`** (384 boyut)

> **Not — Model Tutarsızlığı:** İlk yükleme için `postgre_to_pinecone.py` dosyasında `all-MiniLM-L12-v2` (384 boyut) kullanılıp indeks de `dimension=384` ile oluşturulmuştur. Ancak `RAG_with_langchin.py`, `atomik_veri_execute.py` ve `without_langchain.py` dosyalarında sorgulama ve güncelleme için **`all-mpnet-base-v2`** (768 boyut) kullanılmaktadır. Bu durum iki model arasında bir boyut uyumsuzluğu yaratmaktadır. `deneme.py` ise indeksi `dimension=768` ile oluşturmaktadır. Üretim ortamında tüm pipeline boyunca tek bir model kullanılması önerilir.

Her vektörle birlikte metadata da saklanır:

```python
metadata = {
    "user_id": user_id,
    "user_name": user_name,
    "order_date": str(order_date),
    "products": ["Shampoo (Yellow)", "Body Lotion (Blue)"],
    "categories": ["Personal Care", "Personal Care"]
}
unique_id = f"{user_id}_{order_date}"
embedding_list.append((unique_id, embedding.tolist(), metadata))
```

### 4.3 Pinecone'a Toplu Yükleme

Vektörler 100'lük partiler (batch) halinde Pinecone'a yüklenir:

```python
batch_size = 100
for i in range(0, len(embeddings), batch_size):
    batch = embeddings[i:i + batch_size]
    index.upsert(vectors=batch, namespace="e-commerce")
```

---

## 5. Gerçek Zamanlı Güncelleme (Atomik Senkronizasyon)

**Dosya:** `atomik_veri_execute.py`

PostgreSQL'deki `change_log` tablosu izlenerek yeni veya güncellenen siparişler **10 saniyede bir** Pinecone'a aktarılır:

```python
def sync_with_pinecone():
    while True:
        changed_records = fetch_changed_records()   # İşlenmemiş kayıtları al
        if changed_records:
            documents = prepare(changed_records)    # LangChain Document formatına çevir
            upsert_to_pinecone(documents)           # Pinecone'a gönder
            mark_as_processed(changed_records)      # İşlenmiş olarak işaretle
        time.sleep(10)
```

Bu yöntemde embedding oluşturma işlemi **LangChain** üzerinden yapılır:

```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)
vector_store = PineconeVectorStore.from_documents(
    documents=documents,
    embedding=embeddings,
    index_name="ecommerce-2",
    namespace="ecommerce-22"
)
```

---

## 6. Benzerlik Araması (Similarity Search)

Kullanıcının sorusu aynı embedding modeliyle vektöre çevrilir ve Pinecone'da en yakın 100 komşu aranır.

### 6.1 LangChain Olmadan (Doğrudan API)

**Dosya:** `without_langchain.py` — `search()` fonksiyonu

```python
def search(top_k, query):
    query_vector = model.encode(query).tolist()   # Soruyu vektöre çevir
    docs = index.query(
        vector=query_vector,
        top_k=top_k,                              # En benzer top_k sonucu getir
        include_metadata=True,
        namespace="e-commerce2"
    )
    retrieved_docs = []
    for doc in docs.get('matches', []):
        retrieved_docs.append({
            'metadata': doc['metadata'],
            'score': doc['score']                 # Kosinüs benzerlik skoru
        })
    return retrieved_docs
```

### 6.2 LangChain ile (RetrievalQA Zinciri)

**Dosya:** `RAG_with_langchin.py` — `RAGSystem` sınıfı

```python
self.vector_store = PineconeVectorStore(
    index_name="ecommerce-2",
    embedding=self.embeddings,
    namespace="ecommerce-22"
)

self.qa_chain = RetrievalQA.from_chain_type(
    llm=self.llm,
    chain_type="stuff",
    retriever=self.vector_store.as_retriever(
        search_kwargs={"k": 100}   # En benzer 100 belgeyi getir
    ),
    return_source_documents=True,
    chain_type_kwargs={"prompt": self.prompt}
)
```

---

## 7. RAG (Retrieval-Augmented Generation) Akışı

```
1. Kullanıcı soruyu girer
       │
       ▼
2. Soru embedding modeli ile vektöre çevrilir
   (LangChain yolunda: "all-mpnet-base-v2" / doğrudan yolda: "all-mpnet-base-v2")
       │
       ▼
3. Pinecone'da benzerlik araması yapılır
   (top-100 en yakın sipariş kaydı döner)
       │
       ▼
4. Dönen belgeler bağlam (context) olarak birleştirilir
       │
       ▼
5. Prompt Template'e yerleştirilir:
   "context: `{context}`  question: {question}"
       │
       ▼
6. GPT-4 / GPT-4 Turbo cevabı oluşturur
       │
       ▼
7. Cevap + kaynak belgeler kullanıcıya gösterilir
```

---

## 8. İndeks İzleme

**Dosya:** `RAG_with_langchin.py` — `debug_index()` metodu  
**Dosya:** `without_langchain.py` — `debug_index()` fonksiyonu

```python
def debug_index(self):
    index = self.pc.Index(self.index_name)
    stats = index.describe_index_stats()
    print(f"Toplam vektör sayısı : {stats.total_vector_count}")
    print(f"Namespace'ler        : {stats.namespaces}")
    print(f"Boyut                : {stats.dimension}")
```

---

## 9. Özet Tablo

| Aşama | Dosya | Yöntem |
|-------|-------|--------|
| İndeks oluşturma | `postgre_to_pinecone.py` | `Pinecone.create_index()` (384 boyut, ServerlessSpec) |
| İlk veri yükleme | `postgre_to_pinecone.py` | `SentenceTransformer` → `index.upsert()` |
| Gerçek zamanlı güncelleme | `atomik_veri_execute.py` | `HuggingFaceEmbeddings` → `PineconeVectorStore.from_documents()` |
| Benzerlik araması (doğrudan) | `without_langchain.py` | `index.query(vector, top_k=100)` |
| Benzerlik araması (LangChain) | `RAG_with_langchin.py` | `RetrievalQA` + `as_retriever(k=100)` |
| Cevap üretme | `RAG_with_langchin.py`, `without_langchain.py` | GPT-4 / GPT-4 Turbo |
| İndeks izleme | `RAG_with_langchin.py`, `without_langchain.py` | `index.describe_index_stats()` |
