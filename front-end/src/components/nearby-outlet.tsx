import { ChevronDown, ChevronUp } from "lucide-react";
import type { Outlet } from "@/types/outlet";
import { useState } from "react";

export function NearbyOutletList({
  outlets,
  maxHeight = 300,
}: {
  outlets: Outlet[];
  maxHeight?: number;
}) {
  const [show, setShow] = useState(true);

  if (!outlets || outlets.length === 0) return null;

  return (
    <div
      className="w-full border-t bg-white shadow-lg z-10"
      style={{ maxHeight, overflowY: "auto" }}
    >
      <button
        className="w-full flex items-center justify-between px-6 py-4 font-semibold text-base focus:outline-none"
        onClick={() => setShow((v) => !v)}
        aria-expanded={show}
        aria-controls="nearby-list"
      >
        <span>Nearby Outlets ({outlets.length})</span>
        {show ? (
          <ChevronUp className="w-5 h-5" />
        ) : (
          <ChevronDown className="w-5 h-5" />
        )}
      </button>
      {show && (
        <div className="px-6 pb-4" id="nearby-list">
          <ul>
            {outlets.map((outlet) => (
              <li
                key={outlet.id}
                className="mb-4 pb-4 border-b last:border-b-0"
              >
                <button className="w-full text-left">
                  <div className="font-medium">{outlet.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {outlet.address}
                  </div>
                  {outlet.distance && (
                    <div className="text-xs text-primary">
                      {outlet.distance.toFixed(1)} km away
                    </div>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
