import time
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from sklearn.decomposition import PCA
import streamlit as st
from gensim.models import Word2Vec
from gensim.utils import simple_preprocess
import pandas as pd
import matplotlib.pyplot as plt
from lib.pdf_context import preprocess_pdf_sentences

def run(sentences, source="manual"):
    st.markdown("---")
    st.subheader("🧭 2D Vector Space View")

    # Preprocess the sentences
    if source == "pdf":
        # PDF模式 ➔ 是一整個string，直接用自訂preprocessing
        preprocessed_sentences = preprocess_pdf_sentences(raw_text=sentences, tokenize=False)
        tokenized_sentences = preprocess_pdf_sentences(raw_text=sentences)
    else:
        # 手打textarea模式 ➔ 正常每行一句
        preprocessed_sentences = sentences
        tokenized_sentences = [simple_preprocess(sentence) for sentence in sentences]

    # ❗Error handling: no valid words to train
    flat_tokens = [word for sentence in tokenized_sentences for word in sentence]
    if not tokenized_sentences or not flat_tokens:
        st.error(f"❌ No valid words found in your input. Please enter meaningful sentences with actual words.\n{sentences}\n\n{tokenized_sentences}\n\n{flat_tokens}")
        return

    # Train a Word2Vec model
    model = Word2Vec(tokenized_sentences, vector_size=100, window=5, min_count=1, workers=4)

    # Get the word vectors
    word_vectors = np.array([model.wv[word] for word in model.wv.index_to_key])

    # 防止 PCA 出錯
    if word_vectors.shape[0] < 3 or word_vectors.shape[1] < 3:
        st.error(
            f"❌ Not enough data to perform PCA.\n"
            f"- Found {word_vectors.shape[0]} words (need ≥ 3)\n"
            f"- Word vector dimension is {word_vectors.shape[1]} (need ≥ 3)"
        )
        return

    # Reduce the dimensions to 3D using PCA
    pca = PCA(n_components=3)
    reduced_vectors = pca.fit_transform(word_vectors)

    # print(model.wv.index_to_key)
    # # try to display model.wv.index_to_key and its vector
    # print(model.wv.index_to_key)
    # for word in model.wv.index_to_key:
    #   print(word, model.wv[word])

    cmap = plt.get_cmap('tab20', len(tokenized_sentences))  # 安全使用 N 個顏色
    hex_colors = [
        '#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255))
        for r, g, b, a in [cmap(i) for i in range(len(tokenized_sentences))]
    ]

    # 為每個 word 分配所屬句子的顏色
    word_colors = []
    for word in model.wv.index_to_key:
        for i, sentence in enumerate(tokenized_sentences):
            if word in sentence:
                word_colors.append(hex_colors[i])
                break
    color_map = hex_colors

    word_ids = [f"word-{i}" for i in range(len(model.wv.index_to_key))]

    # Create a 2D scatter plot using Plotly
    scatter = go.Scatter(
        x=reduced_vectors[:, 0],
        y=reduced_vectors[:, 1],
        mode='markers+text',
        text=model.wv.index_to_key,
        textposition='top center',
        marker=dict(color=word_colors, size=8),
        customdata=word_colors,
        ids=word_ids,
        hovertemplate="Word: %{text}<br>Color: %{customdata}",
        name="Words"
    )

    # Create line traces for each displayed sentence
    display_array = [True] * len(tokenized_sentences) # Example display array

    # Create line traces for each sentence
    line_traces = []
    for i, sentence in enumerate(tokenized_sentences):
        if display_array[i]:
            line_vectors = [reduced_vectors[model.wv.key_to_index[word]] for word in sentence]
            line_trace = go.Scatter(
                x=[vector[0] for vector in line_vectors],
                y=[vector[1] for vector in line_vectors],
                mode='lines',
                line=dict(color=color_map[i], width=1, dash='solid'),
                showlegend=True,
                name=f"Sentence {i+1}",  # Customize the legend text
                hoverinfo='all'  # Disable line trace hover info
            )
            # Set different marker symbols for the start and end words
            line_traces.append(line_trace)

    fig = go.Figure(data=[scatter] + line_traces)

    # Set the plot title and axis labels
    fig.update_layout(
        xaxis_title="X",
        yaxis_title="Y",
        title="2D Visualization of Word Embeddings",
        width=1000,  # Custom width
        height=1000  # Custom height
    )

    # Show the input sentences
    with st.expander("📄 Show Input Sentences", expanded=False):
        max_display = 50
        num_sentences = len(preprocessed_sentences)

        if num_sentences > max_display:
            st.markdown(f"⚡ Showing only the first {max_display} of {num_sentences} sentences:")
            display_sentences = preprocessed_sentences[:max_display]
        else:
            display_sentences = preprocessed_sentences

        for i, sentence in enumerate(display_sentences, 1):
            st.markdown(f"**Sentence {i}:** {sentence}")


    # Show the plot
    st.plotly_chart(fig, use_container_width=True, key=f"view2d_plotly_chart_{time.time()}")
