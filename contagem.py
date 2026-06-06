import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
import tiktoken

# Encoding para modelos GPT-3.5 / GPT-4
enc = tiktoken.get_encoding("cl100k_base")

def tokens_mensagem(role, content):
    """Retorna tokens de uma mensagem no formato da API (inclui ~4 tokens de overhead)."""
    return 4 + len(enc.encode(role)) + len(enc.encode(content))

def tokens_conversa(mensagens):
    """Recebe lista de {'role': ..., 'content': ...} e retorna total de tokens da conversa."""
    total = 0
    for msg in mensagens:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        total += tokens_mensagem(role, content)
    total += 2  # token de finalização da conversa
    return total

def processar_arquivo(caminho):
    with open(caminho, 'r', encoding='utf-8') as f:
        texto_bruto = f.read()

    # Tenta interpretar como JSON apenas para verificar se é conversa
    try:
        dados = json.loads(texto_bruto)
        if isinstance(dados, list) and all(isinstance(m, dict) and "role" in m for m in dados):
            # É uma conversa! Conta cada mensagem separadamente
            total = tokens_conversa(dados)
            # Para debug, extrai os conteúdos textuais
            conteudo_debug = " ".join(m.get("content", "") for m in dados if isinstance(m.get("content"), str))
            return total, conteudo_debug, "conversa (lista de mensagens)"
    except Exception:
        pass

    # Qualquer outro caso: trata o texto bruto como uma única mensagem do usuário
    total = tokens_mensagem("user", texto_bruto)
    return total, texto_bruto, "arquivo bruto (user)"

def selecionar_arquivo():
    caminho = filedialog.askopenfilename(
        title="Selecione um arquivo",
        filetypes=[("Todos os suportados", "*.txt *.json *.csv"), ("Todos", "*.*")]
    )
    if not caminho:
        return

    try:
        total, texto, tipo = processar_arquivo(caminho)
        caracteres = len(texto)
        palavras = len(texto.split())

        resultado = f"Tipo: {tipo}\n"
        resultado += f"Tokens para chat: {total}\n"
        resultado += f"Caracteres: {caracteres} | Palavras: {palavras}\n"
        resultado += f"\nPrévia do conteúdo:\n{texto[:200]}..."

        label_resultado.config(text=resultado)
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao processar:\n{e}")

# Interface
janela = tk.Tk()
janela.title("Contador de Tokens – Chat")
janela.geometry("520x340")

btn = tk.Button(janela, text="Selecionar arquivo", command=selecionar_arquivo, font=("Arial", 11))
btn.pack(pady=15)

label_resultado = tk.Label(janela, text="Nenhum arquivo", font=("Consolas", 10), justify="left")
label_resultado.pack(pady=10, padx=15)

janela.mainloop()