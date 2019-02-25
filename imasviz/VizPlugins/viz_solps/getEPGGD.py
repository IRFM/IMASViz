#! /usr/bin/env python3

import logging
import numpy as np

class GetGGDVars:
    names = ['gridGGDSlice', 'GGDSlice']
    numOfParams = len(names)
    gridGGDSlice, GGDSlice = range(numOfParams)

    defaultValues = {}
    defaultValues['gridGGDSlice'] = 0
    defaultValues['GGDSlice'] = 0

class getEPGGD():
    """Get GGD and grid topology.
    """

    def __init__(self, EPids, parent=None):

        self.ep = EPids

    def ggdCheck(self):
        """Checks if the filled grid_ggd structure (contains mandatory grid
        geometry data) is present in the opened IDS. Check also the ggd
        structure (contains data on physics quantities which are not mandatory.
        """
        nGridGGDSlices = len(self.ep.grid_ggd)
        nGGDSlices = len(self.ep.ggd)
        logging.info('Number of grid_ggd slices: ' + str(nGridGGDSlices))
        logging.info('Number of ggd slices: ' + str(nGGDSlices))

        if nGridGGDSlices < 1:
            logging.warning('grid_ggd structure is empty!')
            return

        if nGGDSlices < 1:
            logging.warning('ggd structure is empty!')
            return

    def getNObj(self, gridId=0):

        """Return number of 0D, 1D and 2D objects found in the grid_ggd
        slice.

        Arguments:
            gridId (int) : grid_ggd slice index (array of structure index)
        """

        # Set variables to later hold number of elements
        num_obj_0D = 0
        num_obj_1D = 0
        num_obj_2D = 0

        # Check for nodes, edges and cells data in current IDS database and
        # get number of objects for each dimension
        # objects_per_dimensions(0) holds every 0D object (nodes/vertices).
        num_obj_0D = len(self.ep.grid_ggd[gridId].space[0]. \
            objects_per_dimension[0].object)
        # objects_per_dimensions[1] holds every 1D object (edges)
        num_obj_1D = len(self.ep.grid_ggd[gridId].space[0]. \
            objects_per_dimension[1].object)
        # objects_per_dimensions[2] holds every 2D object (faces/2D cells)
        num_obj_2D = len(self.ep.grid_ggd[gridId].space[0]. \
            objects_per_dimension[2].object)

        logging.info('Grid GGD slice: ' + str(gridId))
        logging.info('Number of 0D objects: ' + str(num_obj_0D))
        logging.info('Number of 1D objects: ' + str(num_obj_1D))
        logging.info('Number of 2D objects: ' + str(num_obj_2D))

        return num_obj_0D, num_obj_1D, num_obj_2D

    def getNGridSubset(self, gridId=0):
        """Return number of grid subsets found in the grid_ggd slice:

        Arguments:
            gridId (int) : grid_ggd slice index (array of structure index)
        """

        return len(self.ep.grid_ggd[gridId].grid_subset)

    def getGridSubsetName(self, gridId=0, gsId=0):
        """Return name of the grid subset identified by index gsId.

        Arguments
            gridId (int) : grid_ggd slice index (array of structure index)
            gsId (int) : Grid subset index
        """
        gs_obj = self.ep.grid_ggd[gridId].grid_subset[gsId]
        return gs_obj.identifier.name

    def getGridSubsetDim(self, gridId=0, gsId=0):
        """Return dimension of the grid subset (checks the dimension of the
        first element.

        Arguments
            gridId (int) : grid_ggd slice index (array of structure index)
            gsId (int) : Grid subset index
        """
        gs_obj = self.ep.grid_ggd[gridId].grid_subset[gsId]
        return gs_obj.element[0].object[0].dimension

    def getGSGridGeometry(self, ggdVars):
        """Return list of nodes/points and connectivity array for quad
        elements.

        """

        gg = ggdVars['gridGGDSlice'] # grid_ggd index
        g = ggdVars['GGDSlice']  # ggd index
        gs_id = ggdVars['gridSubsetId'] - 1

        self.num_obj_0D, self.num_obj_1D, self.num_obj_2D = \
            self.getNObj(gridId=gg)

        # Reading IDS grid geometry and physics quantities array
        nodes = np.zeros(shape=(self.num_obj_0D, 2))
        # quad_conn_array = np.zeros(shape=(self.num_obj_2D, 4), dtype=np.int)
        nElements = len(self.ep.grid_ggd[gg].grid_subset[gs_id].element)
        quad_conn_array = np.zeros(shape=(nElements, 4), dtype=np.int)

        # List of nodes and corresponding coordinates (2D spade - x and y)
        for i in range(self.num_obj_0D):
            # R coordinate
            nodes[i][0] = \
                self.ep.grid_ggd[gg].space[0].objects_per_dimension[0].object[i].geometry[0]
            # Z coordinate
            nodes[i][1] = \
                self.ep.grid_ggd[gg].space[0].objects_per_dimension[0].object[i].geometry[1]

        for i in range(nElements):
            object = self.ep.grid_ggd[gg].grid_subset[gs_id].element[
                i].object[0]
            ind = object.index - 1
            s = object.space - 1
            d = object.dimension - 1

            for j in range(0,4):
                quad_conn_array[i][j] = \
                    self.ep.grid_ggd[gg].space[s].objects_per_dimension[
                        d].object[ind].nodes[j] - 1

        return nodes, quad_conn_array

    def getQuantityDict(self, ggd, gridSubsetId):
        """Get dictionary of available quantities and corresponding values
        for specified grid subset.

        Arguments:
            ggd (object) : GGD slice structure object (e.g.
                           ids.edge_profiles.ggd[0]
            gridSubsetId (int) Grid subset index
        """

        # Dictionary of quantity labels ( = keys) and corresponding structure
        # objects
        quantityDict = \
            {'Electron Density [n/m³]' : {'obj' : ggd.electrons.density},
             'Electron Temperature [eV]' : {'obj' : ggd.electrons.temperature},
             }

        # Include ion array of structure
        for i in range(len(ggd.ion)):
            # Get label
            if ggd.ion[i].label != '':
                ionLabel = ggd.ion[i].label
            else:
                ionLabel = ggd.ion[i].state[0].label
            # Ion density
            for j in range(len(ggd.ion[i].density)):
                # Check if there is actually an array
                if len(ggd.ion[i].density[j].values) > 0:
                    quantityDict['Ion density ' + ionLabel + ' [n/m³]'] = \
                        {'obj': ggd.ion[i].density}
                else:
                    break
            # Ion temperature
            for j in range(len(ggd.ion[i].temperature)):
                # Check if there is actually an array
                if len(ggd.ion[i].temperature[j].values) > 0:
                    quantityDict['Ion temperature ' + ionLabel + ' [eV]'] = \
                        {'obj' : ggd.ion[i].temperature}
                else:
                    break

        # Go through quantity objects and add corresponding quantity array of
        # values
        for qLabel in quantityDict:
            structure = quantityDict[qLabel]['obj']
            for i in range(len(structure)):
                if structure[i].grid_subset_index == gridSubsetId:
                    quantityValues = structure[i].values
                    quantityDict[qLabel]['values'] = quantityValues

        return quantityDict

