import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import pyarrow.parquet as pq
import numpy as np

class VisualizadorParquet:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualizador Parquet - Contagem, Ordenação e Exportação")
        self.root.geometry("1000x700")

        # Frame superior com informações e botões
        frame_top = tk.Frame(root)
        frame_top.pack(pady=10, fill=tk.X, padx=10)

        self.btn_abrir = tk.Button(
            frame_top, text="Abrir Arquivo .parquet", command=self.abrir_arquivo,
            font=("Arial", 11), padx=10, pady=3
        )
        self.btn_abrir.pack(side=tk.LEFT, padx=5)

        self.btn_exportar = tk.Button(
            frame_top, text="Exportar CSV", command=self.exportar_csv,
            font=("Arial", 11), padx=10, pady=3, bg="#e0e0e0"
        )
        self.btn_exportar.pack(side=tk.LEFT, padx=5)

        self.label_total = tk.Label(frame_top, text="Total de linhas: --", font=("Arial", 11), fg="blue")
        self.label_total.pack(side=tk.LEFT, padx=15)

        self.label_exibidas = tk.Label(frame_top, text="| Exibindo: --", font=("Arial", 11))
        self.label_exibidas.pack(side=tk.LEFT, padx=5)

        self.label_selecionadas = tk.Label(
            frame_top, text="| Selecionadas: 0", font=("Arial", 11, "bold"), fg="green"
        )
        self.label_selecionadas.pack(side=tk.LEFT, padx=15)

        # Frame da grade
        frame_grid = tk.Frame(root)
        frame_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.scroll_y = tk.Scrollbar(frame_grid, orient=tk.VERTICAL)
        self.scroll_x = tk.Scrollbar(frame_grid, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(
            frame_grid,
            yscrollcommand=self.scroll_y.set,
            xscrollcommand=self.scroll_x.set,
            selectmode='extended'
        )
        self.scroll_y.config(command=self.tree.yview)
        self.scroll_x.config(command=self.tree.xview)

        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Eventos
        self.tree.bind('<<TreeviewSelect>>', self.atualizar_contagem_selecao)
        self.tree.bind('<Button-1>', self.on_header_click)

        self.df_preview = None
        self.df_exibido = None
        self.total_linhas = 0
        self.sort_col = None
        self.sort_ascending = True

        # Dicionário para mapear iid da Treeview -> índice original do DataFrame
        self.mapeamento_linhas = {}

    # ------------------------------------------------------------
    # Abertura e carregamento
    # ------------------------------------------------------------
    def abrir_arquivo(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione um arquivo Parquet",
            filetypes=[("Arquivos Parquet", "*.parquet"), ("Todos os arquivos", "*.*")]
        )
        if not arquivo:
            return

        try:
            # Total de linhas via metadados
            parquet_file = pq.ParquetFile(arquivo)
            self.total_linhas = parquet_file.metadata.num_rows

            # Preview (200 linhas)
            self.df_preview = pd.read_parquet(arquivo, engine='pyarrow').head(200)

            self.sort_col = None
            self.sort_ascending = True
            self.df_exibido = self.df_preview.copy()

            self.label_total.config(
                text=f"Total de linhas: {self.total_linhas:,}".replace(",", ".")
            )
            self.label_exibidas.config(text=f"| Exibindo: {len(self.df_exibido)} linhas")
            self.label_selecionadas.config(text="| Selecionadas: 0")

            self.preencher_grade()

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível ler o arquivo.\n{str(e)}")

    def preencher_grade(self):
        # Limpar grade e mapeamento
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.mapeamento_linhas.clear()

        if self.df_exibido.empty:
            self.tree["columns"] = []
            self.tree["show"] = "headings"
            return

        colunas = list(self.df_exibido.columns)
        self.tree["columns"] = colunas
        self.tree["show"] = "headings"

        for col in colunas:
            if col == self.sort_col:
                arrow = " ↑" if self.sort_ascending else " ↓"
                display_name = str(col) + arrow
            else:
                display_name = str(col)
            self.tree.heading(col, text=display_name)
            largura = self.calcular_largura_coluna(col)
            self.tree.column(col, width=largura, anchor="center", minwidth=50)

        # Inserir linhas e guardar mapeamento
        for seq, (idx, row) in enumerate(self.df_exibido.iterrows()):
            valores = [self._formatar_valor(v) for v in row]
            iid = str(seq)  # identificador simples sequencial
            self.tree.insert("", "end", iid=iid, values=valores)
            self.mapeamento_linhas[iid] = idx  # guarda índice original do DataFrame

    # ------------------------------------------------------------
    # Ordenação
    # ------------------------------------------------------------
    def on_header_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "heading":
            col_id = self.tree.identify_column(event.x)
            col_index = int(col_id.replace('#', '')) - 1
            if 0 <= col_index < len(self.tree["columns"]):
                col_name = self.tree["columns"][col_index]
                self.ordenar_por_coluna(col_name)

    def ordenar_por_coluna(self, col_name):
        if self.df_exibido is None:
            return

        if self.sort_col == col_name:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_col = col_name
            self.sort_ascending = True

        try:
            self.df_exibido = self.df_exibido.sort_values(
                by=col_name, ascending=self.sort_ascending, na_position='last'
            )
        except Exception:
            messagebox.showwarning("Aviso", f"Não foi possível ordenar pela coluna '{col_name}'.")
            return

        self.preencher_grade()

    # ------------------------------------------------------------
    # Exportação CSV (com mapeamento preciso)
    # ------------------------------------------------------------
    def exportar_csv(self):
        if self.df_exibido is None:
            messagebox.showinfo("Aviso", "Nenhum arquivo foi carregado.")
            return

        selecionados = self.tree.selection()  # lista de iids (strings sequenciais)

        if selecionados:
            # Converte iids para os índices originais do DataFrame
            indices_originais = []
            for iid in selecionados:
                if iid in self.mapeamento_linhas:
                    indices_originais.append(self.mapeamento_linhas[iid])
            if not indices_originais:
                messagebox.showerror("Erro", "Não foi possível identificar as linhas selecionadas.")
                return
            df_exportar = self.df_exibido.loc[indices_originais]
            mensagem = f"Exportando {len(indices_originais)} linha(s) selecionada(s)."
        else:
            # Se nada selecionado, exporta todas as linhas exibidas (comportamento padrão)
            df_exportar = self.df_exibido.copy()
            mensagem = f"Nenhuma linha selecionada. Exportando todas as {len(df_exportar)} linhas exibidas."

        arquivo_csv = filedialog.asksaveasfilename(
            title="Salvar arquivo CSV",
            defaultextension=".csv",
            filetypes=[("CSV (separado por vírgula)", "*.csv")]
        )
        if not arquivo_csv:
            return

        try:
            df_exportar.to_csv(arquivo_csv, index=False, encoding='utf-8-sig')
            messagebox.showinfo("Sucesso", f"{mensagem}\nArquivo salvo com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar CSV.\n{str(e)}")

    # ------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------
    def calcular_largura_coluna(self, col):
        try:
            serie_str = self.df_exibido[col].fillna('').astype(str)
            max_val = serie_str.map(len).max()
            if pd.isna(max_val):
                max_val = 0
            else:
                max_val = int(max_val)
        except Exception:
            max_val = 0
        len_nome = len(str(col))
        largura = max(max_val, len_nome) * 8
        return min(max(largura, 60), 300)

    def _formatar_valor(self, valor):
        if valor is None or (isinstance(valor, float) and np.isnan(valor)):
            return ''
        return str(valor)

    def atualizar_contagem_selecao(self, event=None):
        selecionados = self.tree.selection()
        qtd = len(selecionados)
        self.label_selecionadas.config(text=f"| Selecionadas: {qtd}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VisualizadorParquet(root)
    root.mainloop()