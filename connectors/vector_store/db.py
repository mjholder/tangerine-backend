from flask_sqlalchemy import SQLAlchemy
from langchain_community.docstore.document import Document
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter


db_connection_string = 'postgresql://citrus:citrus@localhost/citrus'
vector_collection_name = 'collection'

MODEL_SOURCE = "ollama"

db = SQLAlchemy()

class Agents(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    system_prompt = db.Column(db.Text, nullable=True)
    filenames = db.Column(db.ARRAY(db.String), default=[], nullable=True)

    def __repr__(self):
        return f'<Agents {self.id}>'


class DocumentIDs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer)
    path = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(50), nullable=False)
    total_chunks = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<DocumentIDs {self.path}{self.filename} with {self.total_chunks} chunks'


class VectorStoreInterface():
    def __init__(self):
        self.store = None
        self.vector_chunk_size = 2000
        self.vector_chunk_overlap = 500

        if MODEL_SOURCE == "ollama":
            self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        elif MODEL_SOURCE == "huggingface":
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    def init_vector_store(self):
        try:
            self.store = PGVector(
                collection_name=vector_collection_name,
                connection_string=db_connection_string,
                embedding_function=self.embeddings,
            )
        except Exception as e:
            print(f"Error init_vector_store: {e}")
        return

    def split_document(self, text, agent_id, filename, path):
        documents = [Document(page_content=text, metadata={"agent_id": agent_id, "filename": filename, "path": path})]
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.vector_chunk_size,
            chunk_overlap=self.vector_chunk_overlap,
            length_function=len,
            is_separator_regex=False
        )
        return text_splitter.split_documents(documents)

    # returns chunk count of document so agents know
    def add_document(self, text, agent_id, filename, path): 
        docs = self.split_document(text, agent_id, filename, path)
        try:
            self.store.add_documents(docs, ids=[f"{agent_id}|{path}{filename}|{chunk}" for chunk in range(len(docs))])
        except Exception as e:
            print(f"Error adding_documents: {e}")
    
    def delete_document(self, agent_id, filename, path, total_chunks):
        import pdb
        pdb.set_trace()
        self.store.delete([f"{agent_id}|{path}{filename}|{chunk}" for chunk in range(total_chunks)])

    def search(self, query, agent_id):
        docs_with_score = self.store.max_marginal_relevance_search_with_score(query=query, filter={"agent_id": agent_id}, k=2)
        return docs_with_score      # list(int, Document(page_content, metadata))


vector_interface = VectorStoreInterface()
