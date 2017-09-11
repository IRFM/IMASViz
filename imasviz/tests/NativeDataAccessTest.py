
import imas
import math


def write_ids():
    #new data entry
    ids_object=imas.ids(12, 0, 0, 0)
    ids_object.create()

    #fill the ids object with data
    ids_object.magnetics.flux_loop.resize(2)
    ids_object.magnetics.ids_properties.comment="Visualisation test for native data"
    ids_object.magnetics.ids_properties.homogeneous_time = 0
    ids_object.magnetics.flux_loop[0].name = 'Flux loop 1'
    ids_object.magnetics.flux_loop[1].name = 'Flux loop 2'
    ids_object.magnetics.flux_loop[0].flux.data.resize(100)
    ids_object.magnetics.flux_loop[1].flux.data.resize(100)
    ids_object.magnetics.flux_loop[0].flux.time.resize(100)
    ids_object.magnetics.flux_loop[1].flux.time.resize(100)

    for i in range(0,100):
        ids_object.magnetics.flux_loop[0].flux.data[i] = math.sin(i)
        ids_object.magnetics.flux_loop[1].flux.data[i] = float(2*i)
        ids_object.magnetics.flux_loop[0].flux.time[i] = float(i)
        ids_object.magnetics.flux_loop[1].flux.time[i] = float(i)

    ids_object.magnetics.put() #put the data into the database

    # fill the ids object with data
    ids_object.magnetics.flux_loop.resize(2)
    ids_object.magnetics.ids_properties.comment = "Visualisation test for native data (occurence 1)"
    ids_object.magnetics.ids_properties.homogeneous_time = 0
    ids_object.magnetics.flux_loop[0].name = 'Flux loop 1'
    ids_object.magnetics.flux_loop[1].name = 'Flux loop 2'
    ids_object.magnetics.flux_loop[0].flux.data.resize(100)
    ids_object.magnetics.flux_loop[1].flux.data.resize(100)
    ids_object.magnetics.flux_loop[0].flux.time.resize(100)
    ids_object.magnetics.flux_loop[1].flux.time.resize(100)

    for i in range(0, 100):
        ids_object.magnetics.flux_loop[0].flux.data[i] = math.cos(i)
        ids_object.magnetics.flux_loop[1].flux.data[i] = float(3 * i)
        ids_object.magnetics.flux_loop[0].flux.time[i] = float(i)
        ids_object.magnetics.flux_loop[1].flux.time[i] = float(i)

    ids_object.magnetics.put(1)  # put the data into the database

    ids_object.close()


if __name__ == "__main__":
    write_ids()