export function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371 // Radius of the Earth in kilometers
  const dLat = deg2rad(lat2 - lat1)
  const dLon = deg2rad(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  const d = R * c // Distance in kilometers
  return d
}

function deg2rad(deg: number): number {
  return deg * (Math.PI / 180)
}

export interface Outlet {
  latitude: number
  longitude: number
  [key: string]: any // Allows for other properties
}

export function filterOutletsWithinRadius(
  outlets: Outlet[],
  centerLat: number,
  centerLng: number,
  radiusKm = 5,
): Outlet[] {
  return outlets
    .map((outlet) => ({
      ...outlet,
      distance: calculateDistance(centerLat, centerLng, outlet.latitude, outlet.longitude),
    }))
    .filter((outlet) => outlet.distance! <= radiusKm)
    .sort((a, b) => a.distance! - b.distance!)
}
