import type { ColumnDef } from "@tanstack/react-table"
import { Check, Copy } from "lucide-react"

import type { ItemPublic } from "@/client"
import { Button } from "@/components/ui/button"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"
import { cn } from "@/lib/utils"
import { ItemActionsMenu } from "./ItemActionsMenu"

type ItemRow = ItemPublic & {
  product_id?: number | null
  price?: number | null
  mrp?: number | null
  brand?: string | null
  product_rating?: number | null
  product_rating_count?: number | null
  product_url?: string | null
  image_url?: string | null
  owner_id?: string
  owner_name?: string | null
  created_at?: string | null
}

function CopyId({ id }: { id: string }) {
  const [copiedText, copy] = useCopyToClipboard()
  const isCopied = copiedText === id

  return (
    <div className="flex items-center gap-1.5 group">
      <span className="font-mono text-xs text-muted-foreground">{id}</span>
      <Button
        variant="ghost"
        size="icon"
        className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={() => copy(id)}
      >
        {isCopied ? (
          <Check className="size-3 text-green-500" />
        ) : (
          <Copy className="size-3" />
        )}
        <span className="sr-only">Copy ID</span>
      </Button>
    </div>
  )
}

export const columns: ColumnDef<ItemRow>[] = [
  {
    accessorKey: "product_id",
    header: "Product ID",
    cell: ({ row }) => {
      const productId = row.original.product_id
      return productId != null ? (
        <span>{productId}</span>
      ) : (
        <span className="italic text-muted-foreground">—</span>
      )
    },
  },
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ row }) => (
      <div className="max-w-md whitespace-normal wrap-break-word font-medium leading-snug">
        {row.original.title}
      </div>
    ),
  },
  {
    accessorKey: "brand",
    header: "Brand",
    cell: ({ row }) => {
      const brand = row.original.brand
      return (
        <span className={cn(!brand && "italic text-muted-foreground")}>
          {brand || "—"}
        </span>
      )
    },
  },
  {
    accessorKey: "price",
    header: "Price",
    cell: ({ row }) => {
      const price = row.original.price
      return (
        <span
          className={cn(
            !price && price !== 0 && "italic text-muted-foreground",
          )}
        >
          {price != null ? `$${price.toFixed(2)}` : "—"}
        </span>
      )
    },
  },
  {
    accessorKey: "mrp",
    header: "MRP",
    cell: ({ row }) => {
      const mrp = row.original.mrp
      return (
        <span className={cn(mrp == null && "italic text-muted-foreground")}>
          {mrp != null ? `$${mrp.toFixed(2)}` : "—"}
        </span>
      )
    },
  },
  {
    accessorKey: "product_rating",
    header: "Rating",
    cell: ({ row }) => {
      const rating = row.original.product_rating
      return (
        <span className={cn(rating == null && "italic text-muted-foreground")}>
          {rating != null ? rating.toFixed(1) : "—"}
        </span>
      )
    },
  },
  {
    accessorKey: "product_rating_count",
    header: "Rating Count",
    cell: ({ row }) => {
      const count = row.original.product_rating_count
      return (
        <span className={cn(count == null && "italic text-muted-foreground")}>
          {count ?? "—"}
        </span>
      )
    },
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => {
      const description = row.original.description
      return (
        <span
          className={cn(
            "max-w-xs break-words text-muted-foreground",
            !description && "italic",
          )}
        >
          {description || "No description"}
        </span>
      )
    },
  },
  {
    accessorKey: "product_url",
    header: "Product URL",
    cell: ({ row }) => {
      const url = row.original.product_url
      if (!url) return <span className="italic text-muted-foreground">—</span>
      return (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="max-w-xs truncate block text-blue-500 hover:underline"
        >
          {url}
        </a>
      )
    },
  },
  {
    accessorKey: "image_url",
    header: "Image URL",
    cell: ({ row }) => {
      const url = row.original.image_url
      if (!url) return <span className="italic text-muted-foreground">—</span>
      return (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="max-w-xs truncate block text-blue-500 hover:underline"
        >
          {url}
        </a>
      )
    },
  },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => {
      const created_at = row.original.created_at
      if (!created_at) return <span className="text-muted-foreground">—</span>
      return (
        <span className="text-muted-foreground text-xs">
          {new Date(created_at).toLocaleDateString()}
        </span>
      )
    },
  },
  {
    accessorKey: "owner_id",
    header: "Owner",
    cell: ({ row }) => {
      const ownerId = row.original.owner_id
      const ownerName = row.original.owner_name
      if (ownerName) {
        return <span>{ownerName}</span>
      }
      return ownerId ? (
        <CopyId id={ownerId} />
      ) : (
        <span className="italic text-muted-foreground">—</span>
      )
    },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <ItemActionsMenu item={row.original} />
      </div>
    ),
  },
]
