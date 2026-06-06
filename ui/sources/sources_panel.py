# SFusion (SYNAPSE Fusion) Mapper
#
# Copyright (C) 2025 Gabriel Moraes - Noxfort Labs
#
# Este programa é software livre: pode redistribuí-lo e/ou modificá-lo
# sob os termos da Licença Pública Geral Affero GNU como publicada pela
# Free Software Foundation, quer a versão 3 da Licença, ou
# (à sua opção) qualquer versão posterior.
#
# Este programa é distribuído na esperança de que seja útil,
# mas SEM QUALQUER GARANTIA; sem mesmo a garantia implícita de
# COMERCIALIZAÇÃO ou ADEQUAÇÃO A UM PROPÓSITO ESPECÍFICO. Veja a
# Licença Pública Geral Affero GNU para mais detalhes.
#
# Deveria ter recebido uma cópia da Licença Pública Geral Affero GNU
# junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

# File: ui/sources/sources_panel.py
# Author: Gabriel Moraes
# Date: November 2025
#    que lista as fontes de dados carregadas.
#    (Modificado para desabilitar o botão "Gerar .db" por padrão)

import logging
from PySide6.QtCore import Qt, Signal, Slot, QPoint
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QRadioButton,
    QHBoxLayout,
    QFrame,
    QMenu,
    QPushButton,
    QSizePolicy
)

from src.utils.i18n import I18nManager
from src.domain.entities import DataSource, AssociationType


class SourcesPanel(QWidget):
    """
    View do painel lateral.
    Exibe a lista de DataSources e os controlos de associação.
    (Modificado para adicionar o botão "Gerar .db")
    """
    
    # Sinais para o SourcesController
    source_selection_changed = Signal(str)
    source_delete_requested = Signal(str)    
    source_modify_type_requested = Signal(str) 
    
    # Sinal para o MainController
    save_config_requested = Signal()

    def __init__(self, i18n: I18nManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._i18n = i18n
        
        # --- 1. Referência para o Botão Salvar ---
        self.save_button = None
        
        self._init_ui()
        logging.info("SourcesPanel (View) inicializado.")

    def _init_ui(self):
        """Constrói os componentes da UI."""
        t = self._i18n.t
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # --- 1. Caixa de Lista de Fontes ---
        sources_group = QGroupBox(t("sources_panel.title"))
        sources_layout = QVBoxLayout(sources_group)
        
        self.sources_list_widget = QListWidget()
        self.sources_list_widget.setSpacing(3)
        
        self.sources_list_widget.currentItemChanged.connect(
            self._on_list_selection_changed
        )
        self.sources_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sources_list_widget.customContextMenuRequested.connect(
            self._on_context_menu
        )

        sources_layout.addWidget(self.sources_list_widget)
        layout.addWidget(sources_group)

        # --- 2. Caixa de Controlo de Associação (Apenas Informativa) ---
        association_group = QGroupBox(t("sources_panel.association_title"))
        association_layout = QVBoxLayout(association_group)
        association_layout.setSpacing(10)

        self.radio_global = QRadioButton(t("sources_panel.radio_global"))
        self.radio_global.setToolTip(t("sources_panel.radio_global_tip"))
        
        self.radio_local = QRadioButton(t("sources_panel.radio_local"))
        self.radio_local.setToolTip(t("sources_panel.radio_local_tip"))
        self.radio_local.setChecked(True)
        
        association_layout.addWidget(self.radio_global)
        association_layout.addWidget(self.radio_local)
        
        association_group.setEnabled(False) 
        self.association_group = association_group

        layout.addWidget(association_group)
        
        # --- 3. BOTÃO (Gerar .db) ---
        
        layout.addStretch(1)
        
        self.save_button = QPushButton(
            QIcon.fromTheme("document-save"),
            t("main_window.action_save_config") # "Gerar .db"
        )
        self.save_button.setToolTip(t("main_window.action_save_config_tip"))
        self.save_button.setFixedHeight(40)
        self.save_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Fixed
        )
        self.save_button.setDefault(True) 
        self.save_button.clicked.connect(self.save_config_requested)
        
        # (Começa desabilitado por padrão)
        self.save_button.setEnabled(False)
        
        layout.addWidget(self.save_button)
        # --- FIM DA ALTERAÇÃO ---


    # --- Slots (Ouvem a UI) ---
    @Slot(QPoint)
    def _on_context_menu(self, pos: QPoint):
        """Chamado quando o utilizador clica com o botão direito na lista."""
        t = self._i18n.t
        
        item = self.sources_list_widget.itemAt(pos)
        if not item:
            return
            
        source_id = item.data(Qt.UserRole)
        if not source_id:
            return

        context_menu = QMenu(self)
        
        modify_action = QAction(t("sources_panel.menu.modify_type"), self)
        modify_action.triggered.connect(
            lambda: self.source_modify_type_requested.emit(source_id)
        )
        context_menu.addAction(modify_action)

        context_menu.addSeparator()

        delete_action = QAction(t("sources_panel.menu.delete"), self)
        
        delete_action.triggered.connect(
            lambda: self.source_delete_requested.emit(source_id)
        )
        context_menu.addAction(delete_action)

        context_menu.exec(self.sources_list_widget.mapToGlobal(pos))
    
    @Slot(QListWidgetItem, QListWidgetItem)
    def _on_list_selection_changed(self, current: QListWidgetItem, previous):
        """Chamado pela QListWidget quando a seleção (clique esquerdo) muda."""
        if current:
            source_id = current.data(Qt.UserRole)
            self.source_selection_changed.emit(source_id)
        else:
            self.source_selection_changed.emit("")

    # --- Métodos Públicos (Chamados pelo Controller) ---

    @Slot(list)
    def update_sources_list(self, data_sources: list[DataSource]):
        """Atualiza a QListWidget com os dados do AppState."""
        self.sources_list_widget.clear()
        
        if not data_sources:
            return
            
        for source in data_sources:
            item = QListWidgetItem(source.name)
            
            if source.association_type == AssociationType.GLOBAL:
                item.setToolTip(f"Tipo: Global\nCaminho: {source.path}")
            elif source.associated_element_id:
                item.setToolTip(f"Tipo: Local (Associado a {source.associated_element_id})\nCaminho: {source.path}")
            else:
                item.setToolTip(f"Tipo: Local (Não associado)\nCaminho: {source.path}")

            item.setData(Qt.UserRole, source.path) 
            self.sources_list_widget.addItem(item)
    
    @Slot(str)
    def set_selected_source(self, source_id: str):
        """Define a seleção na lista."""
        if not source_id:
            self.sources_list_widget.clearSelection()
            return
            
        for i in range(self.sources_list_widget.count()):
            item = self.sources_list_widget.item(i)
            if item.data(Qt.UserRole) == source_id:
                item.setSelected(True)
                return

    @Slot(str)
    def set_association_type(self, assoc_type: str):
        """Define os botões de rádio (Apenas exibição)."""
        self.radio_global.setAutoExclusive(False)
        self.radio_local.setAutoExclusive(False)
        
        if assoc_type.upper() == "GLOBAL":
            self.radio_global.setChecked(True)
            self.radio_local.setChecked(False) 
        else:
            self.radio_global.setChecked(False) 
            self.radio_local.setChecked(True)
            
        self.radio_global.setAutoExclusive(True)
        self.radio_local.setAutoExclusive(True)

    # --- 4. NOVO SLOT (Ouve o AppState) ---
    @Slot(bool)
    def set_savable_state(self, is_savable: bool):
        """
        Habilita ou desabilita o botão 'Gerar .db' principal.
        Chamado pelo sinal 'savable_state_changed' do AppState.
        """
        if self.save_button:
            self.save_button.setEnabled(is_savable)