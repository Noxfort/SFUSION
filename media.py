import tkinter as tk
from tkinter import messagebox

def calcular_media_harmonica():
    entrada = entry_valores.get().strip()
    if not entrada:
        messagebox.showerror("Erro", "Campo vazio. Digite os valores separados por vírgula.")
        return
    try:
        # Converte a string em lista de floats, ignorando espaços extras
        valores = [float(x.strip()) for x in entrada.split(',') if x.strip() != '']
    except ValueError:
        messagebox.showerror("Erro", "Entrada inválida. Use apenas números separados por vírgula.")
        return

    # Verifica se todos os valores são positivos (exigência da média harmônica)
    if any(v <= 0 for v in valores):
        messagebox.showerror("Erro", "Todos os valores devem ser maiores que zero.")
        return

    # Cálculo: H = n / (1/x1 + 1/x2 + ... + 1/xn)
    n = len(valores)
    soma_inversos = sum(1/v for v in valores)
    media_harmonica = n / soma_inversos

    label_resultado.config(text=f"Média Harmônica: {media_harmonica:.4f}")

# Criação da janela principal
janela = tk.Tk()
janela.title("Calculadora de Média Harmônica")
janela.geometry("400x200")

# Rótulo e entrada
tk.Label(janela, text="Digite os valores separados por vírgula:").pack(pady=10)
entry_valores = tk.Entry(janela, width=40)
entry_valores.pack()

# Botão de cálculo
btn_calcular = tk.Button(janela, text="Calcular Média Harmônica", command=calcular_media_harmonica)
btn_calcular.pack(pady=10)

# Rótulo de resultado
label_resultado = tk.Label(janela, text="", font=("Arial", 12))
label_resultado.pack(pady=10)

# Inicia o loop da interface
janela.mainloop()