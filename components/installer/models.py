from PyQt6.QtCore import QAbstractListModel, QModelIndex, QVariant, Qt, pyqtSignal
from .utils import format_pypi_tooltip_html

DataRole = Qt.ItemDataRole.UserRole + 1


class LibraryListModel(QAbstractListModel):
    """
    A custom QAbstractListModel for managing and presenting PyPI library data
    to a QListView.

    This model stores a list of dictionaries, where each dictionary represents
    a PyPI package and can include details like 'name', 'version', 'status'
    (e.g., 'install', 'installed', 'installing', 'failed'), and a 'description'
    (which is pre-formatted HTML for a tooltip).

    It provides data for display and custom roles, handles updates to library
    details fetched from an external source, and signals when items are removed.

    Signals:
        remove_item (str): Emitted with the name of the library that has been removed from the model (e.g., if its version is "UNKNOWN").
    """

    remove_item = pyqtSignal(str)

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data = data if data else []
        self.name_to_row = {}

    def set_name_to_row(self):
        self.name_to_row = {data["name"]: i for i, data in enumerate(self._data)}

    def rowCount(self, parent=None):
        return len(self._data)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return QVariant()

        row_item = self._data[index.row()]
        if role == DataRole:
            return row_item
        if role == Qt.ItemDataRole.DisplayRole:
            return row_item.get("name", "")

        return QVariant()

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    def setDataList(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def _delete_updated_data(self, indexes):
        for idx, item in indexes.items():
            item_to_remove = [
                index for index, data in enumerate(self._data) if data["name"] == item
            ]
            self._data.pop(item_to_remove[0])
            self.remove_item.emit(item)
            model_index = self.index(idx, 0, QModelIndex())
            self.dataChanged.emit(model_index, model_index)

    def updateData(self, data_dict: dict):
        # When the API has emitted some data related to the library
        indexes_to_remove = {}
        for _, (item, item_data) in enumerate(data_dict.items()):
            index_number = self.name_to_row.get(item, -1)
            if index_number == -1:
                continue
            tootlip = format_pypi_tooltip_html(item_data, "figtree")
            if item_data.get("info", {}).get("summary") == "":
                indexes_to_remove[index_number] = item
            self._data[index_number].update({"description": tootlip})
            self._data[index_number].update({"version": item_data["info"]["version"]})
            idx = self.index(index_number, 0, QModelIndex())
            self.dataChanged.emit(idx, idx)

        self._delete_updated_data(indexes_to_remove)
