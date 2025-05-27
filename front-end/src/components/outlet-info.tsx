"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MapPin, Clock, Navigation, X } from "lucide-react";
import type { Outlet } from "@/types/outlet";
import { NearbyOutletList } from "./nearby-outlet";

interface OutletInfoProps {
  outlet: Outlet | null;
  nearbyOutlets?: Outlet[];
  onClose: () => void;
  radius: number;
  setRadius: (radius: number) => void;
  onRadiusChange: (radius: number) => void;
}

export function OutletInfo({
  outlet,
  onClose,
  nearbyOutlets,
  radius,
  setRadius,
  onRadiusChange,
}: OutletInfoProps) {
  if (!outlet) return null;

  const handleWazeClick = () => {
    if (outlet.waze_link) {
      window.open(outlet.waze_link, "_blank");
    }
  };

  return (
    <Card className="absolute top-15 left-4 w-80 z-10 shadow-lg">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg">{outlet.name}</CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-start gap-2">
          <MapPin className="w-4 h-4 mt-0.5 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{outlet.address}</p>
        </div>

        {outlet.operating_hours && (
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              {outlet.operating_hours}
            </p>
          </div>
        )}

        {outlet.distance && (
          <div className="text-sm text-muted-foreground">
            Distance: {outlet.distance.toFixed(1)} km away
          </div>
        )}

        {outlet.waze_link && (
          <Button onClick={handleWazeClick} className="w-full" size="sm">
            <Navigation className="w-4 h-4 mr-2" />
            Get Directions
          </Button>
        )}

        {/* Radius slider */}
        <div className="flex items-center gap-2 mb-4">
          <label htmlFor="radius" className="text-xs text-muted-foreground">
            Radius:
          </label>
          <input
            id="radius"
            type="range"
            min={1}
            max={20}
            value={radius}
            onChange={(e) => {
              const newRadius = Number(e.target.value);
              setRadius(newRadius);
              onRadiusChange(newRadius); // <-- call fetchNearbyOutlets here
            }}
            className="flex-1"
          />
          <span className="text-xs w-8 text-right">{radius}km</span>
        </div>

        {/* Nearby outlets below radius slider */}
        <NearbyOutletList outlets={nearbyOutlets ?? []} />
      </CardContent>
    </Card>
  );
}
