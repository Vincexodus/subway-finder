"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { Chatbot } from "./chatbot";
import { MessageCircle, MapPin, Clock, Search, X } from "lucide-react";
import type { Outlet } from "@/types/outlet";
import { useRef } from "react";

// Add to props
interface AppSidebarProps {
  outlets: Outlet[];
  onOutletSelect: (outlet: Outlet) => void;
  onSearch: (searchTerm: string) => void;
  nearbyOutlets?: Outlet[];
}

// Use props instead of local state
export function AppSidebar({
  outlets,
  onOutletSelect,
  onSearch,
}: AppSidebarProps) {
  const [showChatbot, setShowChatbot] = useState(false);
  const { state } = useSidebar();
  const mapRef = useRef<{ clearMarkers: () => void }>(null);

  // Search state
  const [searchTerm, setSearchTerm] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  // Filter outlets by name as user types
  const filteredOutlets =
    searchTerm.trim() === ""
      ? outlets
      : outlets.filter((outlet) =>
          outlet.name.toLowerCase().includes(searchTerm.toLowerCase())
        );

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setHasSearched(true);
    onSearch(searchTerm);
  };

  const handleClearSearch = () => {
    setSearchTerm("");
    setHasSearched(false);
    mapRef.current?.clearMarkers();
  };

  if (showChatbot) {
    return (
      <Sidebar>
        <SidebarHeader>
          <Button
            variant="ghost"
            onClick={() => setShowChatbot(false)}
            className="justify-start"
          >
            ← Back to search
          </Button>
        </SidebarHeader>
        <SidebarContent>
          <Chatbot />
        </SidebarContent>
      </Sidebar>
    );
  }

  return (
    <div className="resize-x overflow-auto min-w-[220px] max-w-[400px]">
      <Sidebar>
        <SidebarHeader>
          <form
            onSubmit={handleSearch}
            className="flex items-center gap-2 mb-2"
          >
            <div className="relative flex-1">
              <input
                type="text"
                className="w-full px-2 py-1 border rounded text-sm pr-7"
                placeholder="Search outlet..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="absolute right-1 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
                  aria-label="Clear search"
                  tabIndex={0}
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            <button
              type="submit"
              className="p-2 rounded bg-primary text-white hover:bg-primary/90"
              aria-label="Search"
            >
              <Search className="w-4 h-4" />
            </button>
          </form>
        </SidebarHeader>

        <SidebarContent>
          <ScrollArea className="flex-1">
            <SidebarMenu>
              {filteredOutlets.map((outlet) => (
                <SidebarMenuItem key={outlet.id}>
                  <SidebarMenuButton
                    onClick={() => onOutletSelect(outlet)}
                    className="h-auto p-3 flex-col items-start"
                  >
                    <div className="w-full">
                      <div className="font-medium text-left break-words">
                        {outlet.name}
                      </div>
                      <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground break-words">
                        <MapPin className="w-3 h-3" />
                        <span className="break-words">{outlet.address}</span>
                      </div>
                      {outlet.operating_hours && (
                        <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground break-words">
                          <Clock className="w-3 h-3" />
                          <span className="break-words">
                            {outlet.operating_hours}
                          </span>
                        </div>
                      )}
                      {outlet.distance && (
                        <div className="text-xs text-primary mt-1 break-words">
                          {outlet.distance.toFixed(1)} km away
                        </div>
                      )}
                    </div>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </ScrollArea>
        </SidebarContent>

        <SidebarFooter>
          <Separator />
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton onClick={() => setShowChatbot(true)}>
                <MessageCircle className="w-4 h-4" />
                <span>Ask Assistant</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>
    </div>
  );
}
