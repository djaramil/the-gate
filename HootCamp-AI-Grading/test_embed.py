from sentence_transformers import SentenceTransformer
m = SentenceTransformer("all-mpnet-base-v2")
emb = m.encode(["test chunk","another chunk"], show_progress_bar=False)
print("Encoded", len(emb), "vectors of dim", len(emb[0]))
