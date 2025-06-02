import streamlit as st
import nltk
import pandas as pd
import plotly.express as px
from gensim.models import Word2Vec
from gensim.utils import simple_preprocess
from sklearn.decomposition import PCA
from nltk.corpus import stopwords
from lib.pdf_context import preprocess_pdf_sentences
from ui_utils.ui_utils import display_pretty_table

# --- 確保 nltk 資料齊全 ---
nltk_packages = ['punkt', 'brown', 'stopwords']
for pkg in nltk_packages:
    try:
        nltk.data.find(f'corpora/{pkg}' if pkg != 'punkt' else f'tokenizers/{pkg}')
    except LookupError:
        nltk.download(pkg, quiet=True)

EN_STOPWORDS = set(stopwords.words('english'))

def init_session_state():
    defaults = {
        "vector_size": 100,
        "window_size": 5,
        "min_count": 1,
        "workers": 4,
        "sg": 1,
        "user_sentences": "",
        "query_word": "",
        "trained_model": None,  # ⭐️ 加這個
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

def clean_and_tokenize(sentences):
    tokenized = []
    for sentence in sentences:
        if sentence.strip():
            tokens = simple_preprocess(sentence)
            filtered = [word for word in tokens if word not in EN_STOPWORDS]
            if filtered:
                tokenized.append(filtered)
    return tokenized

def train_word2vec(tokenized_sentences):
    model = Word2Vec(
        vector_size=st.session_state.vector_size,
        window=st.session_state.window_size,
        min_count=st.session_state.min_count,
        workers=st.session_state.workers,
        sg=st.session_state.sg
    )

    model.build_vocab(tokenized_sentences)
    if len(model.wv) == 0:
        st.error(f"❌ Vocabulary is empty after applying Min Word Count = {st.session_state.min_count}.")
        st.info("🔔 Try lowering 'Min Word Count' or adding more input sentences.")
        st.stop()

    model.train(tokenized_sentences, total_examples=len(tokenized_sentences), epochs=model.epochs)
    return model

def plot_embeddings(model, query_words):
    vectors, labels = [], []
    for word in query_words:
        if word in model.wv:
            vectors.append(model.wv[word])
            labels.append(word)

    if len(vectors) < 2:
        st.warning("⚠️ Not enough words found in vocabulary for plotting.")
        return

    reduced = PCA(n_components=2).fit_transform(vectors)

    df = pd.DataFrame({
        'X': reduced[:, 0],
        'Y': reduced[:, 1],
        'Word': labels
    })

    df['Legend_Label'] = df['Word'].apply(lambda x: 'Query Word (Red)' if x == query_words[0] else 'Other Words (Blue)')

    fig = px.scatter(
        df,
        x='X',
        y='Y',
        text='Word',
        color='Legend_Label',
        color_discrete_map={
            'Query Word (Red)': 'red',
            'Other Words (Blue)': 'blue'
        },
        title="Word Embeddings Visualization",
    )

    fig.update_traces(marker=dict(size=10))  # 點點大一點
    st.plotly_chart(fig, use_container_width=True)

def run(sentences=None, source="manual"):
    st.markdown("---")

    init_session_state()

    # --- Prepare processed sentences ---
    if source == "pdf":
        if sentences:
            processed_sentences = preprocess_pdf_sentences(raw_text=sentences, tokenize=True)
        else:
            st.error("❌ No PDF sentences loaded.")
            st.stop()
    elif source == "manual":
        if sentences:
            processed_sentences = sentences
        else:
            processed_sentences = [" ".join(sent) for sent in nltk.corpus.brown.sents()]
    else:
        st.error(f"❌ Unknown source '{source}'.")
        st.stop()

    tokenized_preview = clean_and_tokenize(processed_sentences)
    total_sentences = len(tokenized_preview)
    total_tokens = sum(len(tokens) for tokens in tokenized_preview)
    st.info(f"📚 Prepared **{total_sentences}** tokenized sentences, total **{total_tokens}** tokens.")

    st.markdown("---")
    st.subheader("🧠 CBOW and Skip-Gram Word2Vec Trainer")

    with st.expander("⚙️ Model Settings", expanded=True):
        st.session_state.vector_size = st.slider("Vector Size", 50, 300, 100, step=10)
        st.session_state.window_size = st.slider("Window Size", 2, 10, 5)
        st.session_state.min_count = st.slider("Min Word Count", 1, 5, 1)
        st.session_state.workers = st.slider("Number of Workers", 1, 8, 4)
        model_type = st.radio("Training Algorithm", ["Skip-Gram", "CBOW"], index=0)
        st.session_state.sg = 1 if model_type == "Skip-Gram" else 0

    if st.button("🚀 Train Word2Vec Model"):
        tokenized_sentences = clean_and_tokenize(processed_sentences)

        if not tokenized_sentences:
            st.error("❌ No valid tokenized sentences found after preprocessing.")
            st.stop()

        model = train_word2vec(tokenized_sentences)

        st.session_state.trained_model = model  # save model to session state

        if source == "pdf":
            st.success("✅ Model trained successfully from **PDF content**!")
        elif sentences:
            st.success("✅ Model trained successfully from **manual input**!")
        else:
            st.success("✅ Model trained successfully from **default `Brown` corpus**!")

    st.markdown("---")

    # --- 🔥 查詢模式 ---
    model = st.session_state.get("trained_model", None)

    if model:
        with st.expander("🔍 Query Word", expanded=True):
            if model.wv.index_to_key:
                st.session_state.query_word = st.selectbox(
                    "Choose a word to find similar words:",
                    options=model.wv.index_to_key
                )

                if st.session_state.query_word in model.wv:
                    st.markdown(f"### 🔥 Similar Words to `{st.session_state.query_word}`:")
                    similar_words = model.wv.most_similar(st.session_state.query_word, topn=5)
                    df = pd.DataFrame(similar_words, columns=["Word", "Similarity"]).reset_index(drop=True)
                    display_pretty_table(df)

                if st.button("🔎 Show Embedding Visualization"):
                    sample_words = [st.session_state.query_word] + [word for word, _ in model.wv.most_similar(st.session_state.query_word, topn=5)]
                    plot_embeddings(model, sample_words)
            else:
                st.warning("⚠️ No words available in the model vocabulary.")
    else:
        st.warning("⚠️ No trained model found. Please train the model first.")

