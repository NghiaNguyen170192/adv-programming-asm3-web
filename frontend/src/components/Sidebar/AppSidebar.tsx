import { Home, MessageSquare, Search, ShoppingBag, ShoppingCart, Tag, Users } from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [
  { icon: Home, title: "Home", path: "/" },
  { icon: Search, title: "Search", path: "/search" },
  { icon: ShoppingBag, title: "Products", path: "/items" },
  { icon: ShoppingCart, title: "Cart", path: "/cart" },
  { icon: MessageSquare, title: "Reviews", path: "/reviews" },
  { icon: Tag, title: "Tags", path: "/tags" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const items = currentUser?.is_superuser
    ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
    : baseItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-5 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <span className="text-lg font-bold tracking-widest uppercase text-sidebar-foreground group-data-[collapsible=icon]:hidden">
          XEPHORA
        </span>
        <span className="text-lg font-bold text-sidebar-foreground hidden group-data-[collapsible=icon]:block">
          X
        </span>
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
