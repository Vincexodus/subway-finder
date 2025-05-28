"use client";

import { useState, useRef, useEffect } from "react";
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
} from "@/components/ui/sidebar";
import { Chatbot } from "./chatbot";
import { MessageCircle, MapPin, Clock, Search, X, Menu } from "lucide-react";
import type { Outlet } from "@/types/outlet";

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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(320); // px
  const minSidebarWidth = 200;
  const maxSidebarWidth = 400;
  const resizing = useRef(false);

  // Collapse sidebar automatically on small screens (e.g., < 640px)
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 640) {
        setSidebarCollapsed(true);
      } else {
        setSidebarCollapsed(false);
      }
    };
    handleResize(); // Run on mount
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Sidebar resizing logic
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizing.current || sidebarCollapsed) return;
      // Calculate new width based on mouse X position and sidebar's left offset
      const sidebar = document.getElementById("app-sidebar");
      if (sidebar) {
        const left = sidebar.getBoundingClientRect().left;
        const newWidth = Math.min(
          Math.max(e.clientX - left, minSidebarWidth),
          maxSidebarWidth
        );
        setSidebarWidth(newWidth);
      }
    };
    const handleMouseUp = () => {
      resizing.current = false;
      document.body.style.cursor = "";
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [sidebarCollapsed]);

  const handleMouseDown = () => {
    resizing.current = true;
    document.body.style.cursor = "col-resize";
  };

  // Search state
  const [searchTerm, setSearchTerm] = useState("");

  // Filter outlets by name as user types
  const filteredOutlets =
    searchTerm.trim() === ""
      ? outlets
      : outlets.filter((outlet) =>
          outlet.name.toLowerCase().includes(searchTerm.toLowerCase())
        );

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    onSearch(searchTerm);
  };

  const handleClearSearch = () => {
    setSearchTerm("");
  };

  if (showChatbot) {
    return (
      <div
        className="relative h-full"
        style={{
          width: sidebarCollapsed ? 48 : sidebarWidth,
          minWidth: sidebarCollapsed ? 48 : minSidebarWidth,
          maxWidth: maxSidebarWidth,
          transition: "width 0.2s",
          overflow: "hidden",
        }}
      >
        {/* Collapse/Expand Button */}
        {!showChatbot && (
          <button
            className="absolute top-2 right-2 z-40 bg-gray-100 rounded p-1 hover:bg-gray-200 transition"
            onClick={() => setSidebarCollapsed((c) => !c)}
            aria-label={
              sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"
            }
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {!sidebarCollapsed && (
          <Sidebar
            className="h-full flex flex-col w-full"
            style={{
              minWidth: minSidebarWidth,
              maxWidth: maxSidebarWidth,
            }}
          >
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
        )}
        {/* Resize handle */}
        {!sidebarCollapsed && (
          <div
            className="absolute top-0 right-0 h-full w-2 cursor-col-resize z-50"
            style={{ userSelect: "none" }}
            onMouseDown={handleMouseDown}
          />
        )}
      </div>
    );
  }

  return (
    <div
      id="app-sidebar"
      className="relative h-full"
      style={{
        width: sidebarCollapsed ? 48 : sidebarWidth,
        minWidth: sidebarCollapsed ? 48 : minSidebarWidth,
        maxWidth: maxSidebarWidth,
        transition: "width 0.2s",
        overflow: "hidden",
      }}
    >
      {/* Show only the burger menu when collapsed */}
      {sidebarCollapsed ? (
        <button
          className="absolute top-2 left-1/2 -translate-x-1/2 z-40 bg-gray-100 rounded p-1 hover:bg-gray-200 transition"
          onClick={() => setSidebarCollapsed(false)}
          aria-label="Expand sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
      ) : (
        <>
          <Sidebar
            className="h-full flex flex-col w-full"
            style={{
              minWidth: minSidebarWidth,
              maxWidth: maxSidebarWidth,
            }}
          >
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
                <button
                  type="button"
                  className="p-2 rounded bg-gray-100 hover:bg-gray-200 transition ml-auto"
                  onClick={() => setSidebarCollapsed(true)}
                  aria-label="Collapse sidebar"
                >
                  <Menu className="w-5 h-5" />
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
                            <span className="break-words">
                              {outlet.address}
                            </span>
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
          {/* Resize handle */}
          <div
            className="absolute top-0 right-0 h-full w-2 cursor-col-resize z-50"
            style={{ userSelect: "none" }}
            onMouseDown={handleMouseDown}
          />
        </>
      )}
    </div>
  );
}
