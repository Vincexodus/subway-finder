"use client";

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import type { Outlet } from "@/types/outlet";

interface GoogleMapProps {
  outlets: Outlet[];
  nearbyOutlets?: Outlet[];
  onOutletClick: (outlet: Outlet) => void;
  center: { lat: number; lng: number };
  onCenterChange: (center: { lat: number; lng: number }) => void;
}

export const GoogleMap = forwardRef(function GoogleMap(
  {
    outlets,
    nearbyOutlets = [],
    selectedOutlet,
    onOutletClick,
    center,
    onCenterChange,
  }: GoogleMapProps & { selectedOutlet?: Outlet; nearbyOutlets?: Outlet[] },
  ref
) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<google.maps.Map | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Expose clearMarkers to parent via ref
  useImperativeHandle(ref, () => ({
    clearMarkers: () => {
      markersRef.current.forEach((marker) => marker.setMap(null));
      markersRef.current = [];
    },
  }));

  useEffect(() => {
    const initializeMap = async () => {
      if (
        typeof window !== "undefined" &&
        typeof window.google !== "undefined" &&
        mapRef.current
      ) {
        const map = new google.maps.Map(mapRef.current, {
          center,
          zoom: 12,
          styles: [
            {
              featureType: "poi",
              elementType: "labels",
              stylers: [{ visibility: "off" }],
            },
          ],
        });

        mapInstanceRef.current = map;

        // Add center change listener
        map.addListener("center_changed", () => {
          const newCenter = map.getCenter();
          if (newCenter) {
            onCenterChange({
              lat: newCenter.lat(),
              lng: newCenter.lng(),
            });
          }
        });

        setIsLoaded(true);
      }
    };

    if (!window.google) {
      if (!document.querySelector("#google-maps-script")) {
        const script = document.createElement("script");
        script.id = "google-maps-script";
        script.src = `https://maps.googleapis.com/maps/api/js?key=${process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY}&libraries=places`;
        script.async = true;
        script.defer = true;
        script.onload = initializeMap;
        document.head.appendChild(script);
      } else {
        document
          .querySelector("#google-maps-script")!
          .addEventListener("load", initializeMap);
      }
    } else {
      initializeMap();
    }
    // Only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!isLoaded || !mapInstanceRef.current) return;

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.setMap(null));
    markersRef.current = [];

    outlets
      .filter(
        (outlet) =>
          typeof outlet.latitude === "number" &&
          !isNaN(outlet.latitude) &&
          typeof outlet.longitude === "number" &&
          !isNaN(outlet.longitude)
      )
      .forEach((outlet) => {
        let fillColor = "#14532d"; // dark green for default
        if (selectedOutlet && outlet.id === selectedOutlet.id) {
          fillColor = "#ef4444"; // red for selected
        } else if (nearbyOutlets.some((n) => n.id === outlet.id)) {
          fillColor = "#3B82F6"; // blue for nearby
        }

        const marker = new google.maps.Marker({
          position: { lat: outlet.latitude, lng: outlet.longitude },
          map: mapInstanceRef.current ?? undefined,
          title: outlet.name,
          icon: {
            url:
              "data:image/svg+xml;charset=UTF-8," +
              encodeURIComponent(`
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M16 3C10.477 3 6 7.477 6 13c0 6.075 7.09 14.09 9.293 16.293a1 1 0 0 0 1.414 0C18.91 27.09 26 19.075 26 13c0-5.523-4.477-10-10-10zm0 12.5A2.5 2.5 0 1 1 16 10a2.5 2.5 0 0 1 0 5z" fill="${fillColor}" stroke="#fff" stroke-width="2"/>
                </svg>
              `),
            scaledSize: new google.maps.Size(32, 32),
            anchor: new google.maps.Point(16, 32),
          },
        });

        marker.addListener("click", () => {
          onOutletClick(outlet);
        });

        markersRef.current.push(marker);
      });
  }, [outlets, nearbyOutlets, selectedOutlet, onOutletClick, isLoaded]);

  return (
    <div
      ref={mapRef}
      className="w-full h-full"
      style={{ minHeight: "400px" }}
    />
  );
});
