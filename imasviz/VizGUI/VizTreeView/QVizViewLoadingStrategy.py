import os
import logging
from imasviz.VizUtils import QVizGlobalValues

class QVizViewLoadingStrategy:

    def __init__(self, name):
        self.name = name
        self.identifier = None
        self.time_index = None
        self.is_ids_dynamic = False
     
    def setIdentifier(self, identifier):
        self.identifier = identifier
        
    def setIDSIsDynamic(self, is_ids_dynamic):
        self.is_ids_dynamic = is_ids_dynamic
        
    def setIdentifier(self, identifier):
        self.identifier = identifier
        
    def setTimeIndex(self, time_index):
        self.time_index = time_index
        
    def getName(self):
        return self.name
        
    def getIdentifier(self):
        return self.identifier
        
    def getTimeIndex(self):
        return self.time_index
        
    def isIDSDynamic(self):
        return self.is_ids_dynamic
        
    def getLabel(self):
        if self.identifier is None or not self.is_ids_dynamic:
            return None
        if self.identifier == 3:
            return "displaying all time slices"
        elif self.identifier == 1:
            return "displaying first time slice"
        elif self.identifier == 2:
            return "displaying one over 10 time slices"
        elif self.identifier == 4:
            return "displaying time slice with index=" + str(self.time_index)
        
    @staticmethod
    def getAllStrategies():
       viewLoadingStrategies = []
       viewStrategyNames = ["All time slices", "One over 10 time slices", "First time slice only", "Specific time slice only"]
       for name in viewStrategyNames:
           strategy = QVizViewLoadingStrategy(name)
           strategy.setIdentifier(QVizViewLoadingStrategy.getLoadingStrategyIdentifier(strategy))
           viewLoadingStrategies.append(strategy)
       
       return viewLoadingStrategies
    
    @staticmethod
    def getLoadingStrategyIdentifier(viewLoadingStrategy):
       if viewLoadingStrategy is None:
           print("viewLoadingStrategy is None in getLoadingStrategyIdentifier()")
           return 1
           
       strategyName = viewLoadingStrategy.name
       
       if strategyName == "First time slice only":
           return 1
       elif strategyName == "One over 10 time slices":
           return 2
       elif strategyName == "All time slices":
           return 3
       elif strategyName == "Specific time slice only":
           return 4
       else:
           return 1 #default strategy
           
    @staticmethod
    def getDefaultStrategy():
       defaultStrategy = QVizViewLoadingStrategy("First time slice only")
       defaultStrategy.setIdentifier(QVizViewLoadingStrategy.getLoadingStrategyIdentifier(defaultStrategy))
       return defaultStrategy
