import { useEffect, useRef } from 'react'
import ArcGISMap from '@arcgis/core/Map'
import MapView from '@arcgis/core/views/MapView'
import Graphic from '@arcgis/core/Graphic'
import GraphicsLayer from '@arcgis/core/layers/GraphicsLayer'
import '@arcgis/core/assets/esri/themes/dark/main.css'

const Map = ({ mode, points, topLocations, singleQuery, unitLabel = 'µg/m³' }) => {
  const mapRef = useRef(null)

  useEffect(() => {
    if (!mapRef.current) return undefined

    const graphicsLayer = new GraphicsLayer()
    const map = new ArcGISMap({
      basemap: 'dark-gray-vector',
      layers: [graphicsLayer],
    })

    const defaultCenter =
      mode === 'single'
        ? [singleQuery.lon, singleQuery.lat]
        : [points[0]?.lon ?? singleQuery.lon, points[0]?.lat ?? singleQuery.lat]

    const view = new MapView({
      container: mapRef.current,
      map,
      center: defaultCenter,
      zoom: 13,
    })

    if (mode === 'trace' && points.length > 1) {
      const polyline = new Graphic({
        geometry: {
          type: 'polyline',
          paths: [points.map((point) => [point.lon, point.lat])],
        },
        symbol: {
          type: 'simple-line',
          color: '#22d3ee',
          width: 3,
        },
      })
      graphicsLayer.add(polyline)

      topLocations.forEach((location) => {
        graphicsLayer.add(
          new Graphic({
            geometry: {
              type: 'point',
              longitude: location.lon,
              latitude: location.lat,
            },
            symbol: {
              type: 'simple-marker',
              color: '#f97316',
              size: 9,
              outline: { color: '#fb923c', width: 1 },
            },
            attributes: { site: location.site, value: location.avgExposure.toFixed(1) },
            popupTemplate: {
              title: '{site}',
              content: `Avg exposure: {value} ${unitLabel}`,
            },
          }),
        )
      })
    } else {
      graphicsLayer.add(
        new Graphic({
          geometry: {
            type: 'point',
            longitude: singleQuery.lon,
            latitude: singleQuery.lat,
          },
          symbol: {
            type: 'simple-marker',
            color: '#22d3ee',
            size: 10,
            outline: { color: '#67e8f9', width: 1 },
          },
        }),
      )
    }

    return () => {
      view.destroy()
    }
  }, [mode, points, topLocations, singleQuery])

  return (
    <article className="glass w-full rounded-2xl p-4">
      <h3 className="mb-3 text-lg font-semibold text-slate-100">
        {mode === 'trace' ? 'Trace Path & Top Exposure Sites' : 'Single Location Map'}
      </h3>
      <div ref={mapRef} className="h-130 w-full rounded-xl border border-white/10" />
    </article>
  )
}

export default Map