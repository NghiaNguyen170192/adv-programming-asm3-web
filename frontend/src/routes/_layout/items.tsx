import { useQuery, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Suspense, useMemo } from "react"

import { ItemsService, OpenAPI } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import AddItem from "@/components/Items/AddItem"
import { columns } from "@/components/Items/columns"
import PendingItems from "@/components/Pending/PendingItems"

type ReviewPublicRow = {
  rating: number
}

type ReviewsPublicResponse = {
  data: ReviewPublicRow[]
  count: number
}

type ItemsSearchParams = {
  page?: number
}

const ITEMS_PER_PAGE = 50

function getItemsQueryOptions(skip: number) {
  return {
    queryFn: () => ItemsService.readItems({ skip, limit: ITEMS_PER_PAGE }),
    queryKey: ["items", skip],
  }
}

async function readReviewsByItem(
  itemId: string,
): Promise<ReviewsPublicResponse> {
  const token = localStorage.getItem("access_token") || ""
  const response = await fetch(
    `${OpenAPI.BASE}/api/v1/reviews/item/${itemId}?skip=0&limit=1000`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  )

  if (!response.ok) {
    throw new Error("Failed to load reviews")
  }

  return response.json()
}

async function getReviewAggregates(itemIds: string[]) {
  const entries = await Promise.all(
    itemIds.map(async (itemId) => {
      try {
        const reviews = await readReviewsByItem(itemId)
        const ratings = reviews.data
          .map((review) => Number(review.rating))
          .filter((rating) => Number.isFinite(rating))
        const count = ratings.length
        const average =
          count > 0
            ? ratings.reduce((sum, rating) => sum + rating, 0) / count
            : null

        return [
          itemId,
          {
            product_rating: average,
            product_rating_count: count,
          },
        ] as const
      } catch {
        return [
          itemId,
          {
            product_rating: null,
            product_rating_count: 0,
          },
        ] as const
      }
    }),
  )

  return Object.fromEntries(entries)
}

export const Route = createFileRoute("/_layout/items")({
  component: Items,
  validateSearch: (search: Record<string, unknown>): ItemsSearchParams => ({
    page: typeof search.page === "number" ? search.page : 0,
  }),
  head: () => ({
    meta: [
      {
        title: "Items - FastAPI Template",
      },
    ],
  }),
})

function ItemsTableContent() {
  const navigate = useNavigate()
  const { page = 0 } = useSearch({ from: "/_layout/items" })
  const skip = page * ITEMS_PER_PAGE

  const { data: items } = useSuspenseQuery(getItemsQueryOptions(skip))
  const itemIds = useMemo(() => items.data.map((item) => item.id), [items.data])

  const { data: reviewAggregates } = useQuery({
    queryKey: ["item-review-aggregates", itemIds],
    queryFn: () => getReviewAggregates(itemIds),
    enabled: itemIds.length > 0,
  })

  const tableData = useMemo(
    () =>
      items.data.map((item) => ({
        ...item,
        product_rating: reviewAggregates?.[item.id]?.product_rating ?? null,
        product_rating_count:
          reviewAggregates?.[item.id]?.product_rating_count ?? 0,
      })),
    [items.data, reviewAggregates],
  )

  if (items.data.length === 0 && page === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">You don't have any items yet</h3>
        <p className="text-muted-foreground">Add a new item to get started</p>
      </div>
    )
  }

  return (
    <DataTable
      columns={columns}
      data={tableData}
      showPagination
      totalCount={items.count}
      currentPage={page}
      pageSize={ITEMS_PER_PAGE}
      onPageChange={(newPage) =>
        navigate({ to: ".", search: { page: newPage } })
      }
    />
  )
}

function ItemsTable() {
  return (
    <Suspense fallback={<PendingItems />}>
      <ItemsTableContent />
    </Suspense>
  )
}

function Items() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Items</h1>
          <p className="text-muted-foreground">Create and manage your items</p>
        </div>
        <AddItem />
      </div>
      <ItemsTable />
    </div>
  )
}
