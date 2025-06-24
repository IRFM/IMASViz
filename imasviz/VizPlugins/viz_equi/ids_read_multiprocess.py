# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

'''
    Python function that read IDS in parallel for different
    shots in input

    Inputs
    ------
    -list_shot: List of tuples with each tuple composed of: 
    (idsName, shot, run, user, machine)

    Output
    ------
    -IDS ID: id of the different IDS (for each shot requested)
    -list_shot: List of tuples with each tuple composed of: 
    (idsName, shot, run, user, machine)
'''
from concurrent import futures
import imas

def get_name_ids(input_tuple):
    idsName, shot, run, user, machine = input_tuple
    idd = imas.ids(shot, run)
    idd.open_env(user, machine, '3')
    #TODO eval("idd." + idsName + ".get(" + idsName + ")")
    return idd, input_tuple

def ids_read_multiprocess(tuple_list):
    print('len(tuple_list) =', len(tuple_list))
    with futures.ProcessPoolExecutor(max_workers=len(tuple_list)) as executor:
        future_fct = executor.map(get_name_ids, tuple_list)
    list_idd = []
    list_tup = []
    for it_id, it_tup in future_fct:
        list_idd.append(it_id)
        list_tup.append(it_tup)
    return list_idd, list_tup

if __name__ == '__main__':
    # Init
    inp_tup1 = ('interfero_polarimeter', 52203, 0, 'imas_public', 'west', 13)
    inp_tup2 = ('interfero_polarimeter', 52202, 0, 'imas_public', 'west', 13)
    print('(inp_tup1, inp_tup2) =', (inp_tup1, inp_tup2))
    
    # Call function
    list_idd, list_tup = ids_read_multiprocess([inp_tup1, inp_tup2])

    # Print
    count = 1
    for it_tup in list_tup:
        print('tuple_in', count, ' =', it_tup)
        count += 1

    count = 1
    for it_id in list_idd:
        print('id_out', count, ' =', it_id.interfero_polarimeter.time)
        count += 1
