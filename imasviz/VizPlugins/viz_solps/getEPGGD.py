#! /usr/bin/env python3

import logging

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
        num_grid_ggd_slices = len(self.ep.grid_ggd)
        num_ggd_slices = len(self.ep.ggd)
        logging.info('Number of grid_ggd slices: ' + str(num_grid_ggd_slices))
        logging.info('Number of ggd slices: ' + str(num_ggd_slices))

        if num_grid_ggd_slices < 1:
            logging.warning('grid_ggd structure is empty!')
            return

        # Set variables to later hold number of elements
        num_obj_0D = 0
        num_obj_1D = 0
        num_obj_2D = 0

        # Set default ggd_slide_index
        grid_ggd_slice_index = 0
        # Check for nodes, edges and cells data in current IDS database and
        # get number of objects for each dimension
        # objects_per_dimensions(0) holds every 0D object (nodes/vertices).
        num_obj_0D = len(self.ep.grid_ggd[grid_ggd_slice_index].space[0]. \
            objects_per_dimension[0].object)
        # objects_per_dimensions[1] holds every 1D object (edges)
        num_obj_1D = len(self.ep.grid_ggd[grid_ggd_slice_index].space[0]. \
            objects_per_dimension[1].object)
        # objects_per_dimensions[2] holds every 2D object (faces/2D cells)
        num_obj_2D = len(self.ep.grid_ggd[grid_ggd_slice_index].space[0]. \
            objects_per_dimension[2].object)

        logging.info('Grid GGD slice: ' + str(grid_ggd_slice_index))
        logging.info('Number of 0D objects: ' + str(num_obj_0D))
        logging.info('Number of 1D objects: ' + str(num_obj_1D))
        logging.info('Number of 2D objects: ' + str(num_obj_2D))

        return num_obj_0D, num_obj_1D, num_obj_2D

