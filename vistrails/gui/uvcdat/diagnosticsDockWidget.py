from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QListWidgetItem
     
from ui_diagnosticsDockWidget import Ui_DiagnosticDockWidget

class DiagnosticsDockWidget(QtGui.QDockWidget, Ui_DiagnosticDockWidget):
    
    Types = ["AMWG", "LMWG"]
    DisabledTypes = ["OMWG", "PCWG", "MPAS", "Metrics"]
    AllTypes = Types + DisabledTypes

    def __init__(self, parent=None):
        super(DiagnosticsDockWidget, self).__init__(parent)
        self.setupUi(self)
        
        #initialize data
        #@todo: maybe move data to external file to be read in
        self.groups = {'AMWG': {'AMWG Group 1': ['Diagnostics 1', 
                                                 'Diagnostics 2', 
                                                 'Diagnostics 3'],
                                'AMWG Group 2': ['Diagnostics 4',
                                                 'Diagnostics 5', 
                                                 'Diagnostics 6',],
                                'AMWG Group 3': ['Diagnostics 7',
                                                 'Diagnostics 8', 
                                                 'Diagnostics 9',]},
                       'LMWG': {'LMWG Group 1': ['Diagnostics 10', 
                                                 'Diagnostics 11', 
                                                 'Diagnostics 12'],
                                'LMWG Group 2': ['Diagnostics 13',
                                                 'Diagnostics 14', 
                                                 'Diagnostics 15',],
                                'LMWG Group 3': ['Diagnostics 16',
                                                 'Diagnostics 17', 
                                                 'Diagnostics 18',]}}
        
        self.variables = ['Variable 1', 'Variable 2', 'Variable 3']
        self.observations = ['Obs 1', 'Obs 2', 'Obs 3']
        self.seasons = ['DJF', 'JJA', 'MJJ', 'ASO', 'ANN']
        
        #setup signals
        self.comboBoxType.currentIndexChanged.connect(self.setupDiagnosticTree)
        self.buttonBox.clicked.connect(self.buttonClicked)
        self.treeWidget.itemChanged.connect(self.itemChecked)
        
        #keep track of checked item so we can unckeck it if another is checked
        self.checkedItem = None
        
        self.setupDiagnosticsMenu()
        
        self.comboBoxType.addItems(DiagnosticsDockWidget.Types)
        self.comboBoxVariable.addItems(self.variables)
        self.comboBoxObservation.addItems(self.observations)
        self.comboBoxSeason.addItems(self.seasons)
        
    def setupDiagnosticsMenu(self):
        menu = self.parent().menuBar().addMenu('&Diagnostics')
        
        def generateCallBack(x):
            def callBack():
                self.diagnosticTriggered(x)
            return callBack
        
        for diagnosticType in DiagnosticsDockWidget.AllTypes:
            action = QtGui.QAction(diagnosticType, self)
            action.setEnabled(diagnosticType in DiagnosticsDockWidget.Types)
            action.setStatusTip(diagnosticType + " Diagnostics")
            action.triggered.connect(generateCallBack(diagnosticType))
            menu.addAction(action)
            
    def diagnosticTriggered(self, diagnosticType):
        index = self.comboBoxType.findText(diagnosticType)
        self.comboBoxType.setCurrentIndex(index)
        self.show()
        self.raise_()
        
    def setupDiagnosticTree(self, index):
        diagnosticType = str(self.comboBoxType.itemText(index))
        self.treeWidget.clear()
        for groupName, groupValues in self.groups[diagnosticType].items():
            groupItem = QtGui.QTreeWidgetItem(self.treeWidget, [groupName])
            for diagnostic in groupValues:
                diagnosticItem = QtGui.QTreeWidgetItem(groupItem, [diagnostic])
                diagnosticItem.setFlags(diagnosticItem.flags() & (~Qt.ItemIsSelectable))
                diagnosticItem.setCheckState(0, Qt.Unchecked)
        
    def buttonClicked(self, button):
        role = self.buttonBox.buttonRole(button) 
        if role == QtGui.QDialogButtonBox.ApplyRole:
            self.applyClicked()
        elif role == QtGui.QDialogButtonBox.RejectRole:
            self.cancelClicked()
            
    def applyClicked(self):
        diagnostic = str(self.checkedItem.text(0))
        group = str(self.checkedItem.parent().text(0))
        type = str(self.comboBoxType.currentText())
        observation = str(self.comboBoxObservation.currentText())
        variable = str(self.comboBoxVariable.currentText())
        season = str(self.comboBoxSeason.currentText())
        
        print "diagnostic: %s" % diagnostic
        print "group: %s" % group
        print "type: %s" % type
        print "observation: %s" % observation
        print "variable: %s" % variable
        print "season: %s" % season
        
    def cancelClicked(self):
        self.close()
            
    def itemChecked(self, item, column):
        if item.checkState(column) == Qt.Checked:
            if self.checkedItem is not None:
                self.treeWidget.blockSignals(True)
                self.checkedItem.setCheckState(column, Qt.Unchecked)
                self.treeWidget.blockSignals(False)
            self.checkedItem = item
        else:
            self.checkedItem = None