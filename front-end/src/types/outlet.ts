export interface Outlet {
  id: number
  name: string
  address: string
  operating_hours?: string
  waze_link?: string
  longitude: number
  latitude: number
  distance?: number
}

export interface MapCenter {
  lat: number
  lng: number
}
