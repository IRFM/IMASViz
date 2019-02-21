#! /usr/bin/env python3

import logging

class GetGGDVars:
    names = ['grid_ggd_slice', 'ggd_slice']
    numOfParams = len(names)
    grid_ggd_slice, ggd_slice = range(numOfParams)

    defaultValues = {}
    defaultValues[grid_ggd_slice] = '0'
    defaultValues[ggd_slice] = '0'

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



