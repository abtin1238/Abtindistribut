// leaflet.markercluster به متغیر سراسری L وابسته است؛ این ماژول باید قبل از آن import شود.
import L from 'leaflet'
Object.assign(window, { L })
export default L
