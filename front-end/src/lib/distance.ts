export interface Outlet {
  latitude: number;
  longitude: number;
  [key: string]: unknown; // Allows for other properties with safer type
}