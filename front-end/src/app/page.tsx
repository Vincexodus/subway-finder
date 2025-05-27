"use client";

import { useEffect, useState, useRef } from "react";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { GoogleMap } from "@/components/google-map";
import { OutletInfo } from "@/components/outlet-info";
import type { Outlet, MapCenter } from "@/types/outlet";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE;

export default function HomePage() {
  const [outlets, setOutlets] = useState<Outlet[]>([]);
  const [selectedOutlet, setSelectedOutlet] = useState<Outlet | null>(null);
  const [nearbyOutlets, setNearbyOutlets] = useState<Outlet[]>([]);
  const [mapCenter, setMapCenter] = useState<MapCenter>({
    lat: 40.7128,
    lng: -74.006,
  });
  const [radius, setRadius] = useState(5);
  const [loading, setLoading] = useState(true);
  const [, setSearchTerm] = useState("");
  const mapRef = useRef<{ clearMarkers: () => void }>(null);
  const fetchAllOutlets = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/outlets`);
      const data = await response.json();
      setOutlets(data);
      if (data.length > 0) {
        setMapCenter({ lat: data[0].latitude, lng: data[0].longitude });
        setSelectedOutlet(data[0]);
      }
    } catch (error) {
      console.error("Error fetching all outlets:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllOutlets();
  }, []);

  const handleOutletInfoClose = () => {
    setSelectedOutlet(null);
    setNearbyOutlets([]);
    mapRef.current?.clearMarkers();
  };

  const selectOutletAndFetchNearby = async (
    outlet: Outlet,
    radiusValue?: number
  ) => {
    setSelectedOutlet(outlet);
    setMapCenter({ lat: outlet.latitude, lng: outlet.longitude });

    const radiusToUse = typeof radiusValue === "number" ? radiusValue : radius;
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/outlets/nearby?latitude=${outlet.latitude}&longitude=${outlet.longitude}&distance_km=${radiusToUse}`
      );
      const data = await response.json();
      setNearbyOutlets(data.filter((o: Outlet) => o.id !== outlet.id));
    } catch (error) {
      console.error("Error fetching nearby outlets:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleMapCenterChange = (center: MapCenter) => {
    setMapCenter(center);
  };

  return (
    <SidebarProvider>
      <div className="flex h-screen w-full">
        <AppSidebar
          outlets={outlets}
          onOutletSelect={selectOutletAndFetchNearby}
          onSearch={(searchTerm: string) => setSearchTerm(searchTerm)}
          nearbyOutlets={nearbyOutlets}
        />

        <main className="flex-1 flex flex-col relative">
          {/* Map fills available space */}
          <div className="flex-1  relative">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                  <p>Loading outlets...</p>
                </div>
              </div>
            ) : (
              <GoogleMap
                outlets={outlets}
                nearbyOutlets={nearbyOutlets}
                selectedOutlet={selectedOutlet ?? undefined}
                onOutletClick={selectOutletAndFetchNearby}
                center={mapCenter}
                onCenterChange={handleMapCenterChange}
              />
            )}
          </div>
          {/* OutletInfo at the bottom */}
          {selectedOutlet && (
            <div className="w-full border-t bg-white shadow-lg z-20">
              <OutletInfo
                outlet={selectedOutlet}
                onClose={handleOutletInfoClose}
                nearbyOutlets={nearbyOutlets}
                radius={radius}
                setRadius={setRadius}
                onRadiusChange={(newRadius) => {
                  if (selectedOutlet) {
                    selectOutletAndFetchNearby(selectedOutlet, newRadius);
                  }
                }}
              />
            </div>
          )}
        </main>
      </div>
    </SidebarProvider>
  );
}
