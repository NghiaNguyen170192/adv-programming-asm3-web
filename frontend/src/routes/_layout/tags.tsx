import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { Tag, Trash2 } from "lucide-react"
import { useState } from "react"

import { OpenAPI } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"

type TagPublic = {
  id: string
  name: string
}

// ─── API helpers ──────────────────────────────────────────────────────────────

function authHeaders() {
  return {
    Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
    "Content-Type": "application/json",
  }
}

async function readTags(): Promise<TagPublic[]> {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/tags/`, {
    headers: authHeaders(),
  })
  if (!response.ok) throw new Error("Failed to load tags")
  return response.json()
}

async function createTag(name: string): Promise<TagPublic> {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/tags/`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ name }),
  })
  if (!response.ok) throw new Error((await response.text()) || "Failed to create tag")
  return response.json()
}

async function deleteTag(id: string): Promise<void> {
  const response = await fetch(`${OpenAPI.BASE}/api/v1/tags/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  })
  if (!response.ok) throw new Error((await response.text()) || "Failed to delete tag")
}

// ─── Delete cell ─────────────────────────────────────────────────────────────

function DeleteTagCell({ tag }: { tag: TagPublic }) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [open, setOpen] = useState(false)

  const mutation = useMutation({
    mutationFn: () => deleteTag(tag.id),
    onSuccess: () => {
      showSuccessToast("Tag deleted successfully")
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ["tags"] })
    },
    onError: (e: Error) => showErrorToast(e.message || "Failed to delete tag"),
  })

  return (
    <div className="flex justify-end">
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="icon">
            <Trash2 className="size-4 text-destructive" />
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Tag</DialogTitle>
            <DialogDescription>
              Tag <strong>"{tag.name}"</strong> will be permanently deleted. Are you sure?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={mutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              loading={mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ─── Columns ─────────────────────────────────────────────────────────────────

const columns: ColumnDef<TagPublic>[] = [
  { accessorKey: "name", header: "Name" },
  { accessorKey: "id", header: "ID" },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => <DeleteTagCell tag={row.original} />,
  },
]

// ─── Route ───────────────────────────────────────────────────────────────────

export const Route = createFileRoute("/_layout/tags")({
  component: Tags,
  head: () => ({
    meta: [{ title: "Tags - FastAPI Template" }],
  }),
})

function Tags() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState("")

  const { data: tags = [], isLoading } = useQuery({
    queryKey: ["tags"],
    queryFn: readTags,
  })

  const createMutation = useMutation({
    mutationFn: () => createTag(name.trim()),
    onSuccess: () => {
      showSuccessToast("Tag created successfully")
      setIsOpen(false)
      setName("")
      queryClient.invalidateQueries({ queryKey: ["tags"] })
    },
    onError: (e: Error) => showErrorToast(e.message || "Failed to create tag"),
  })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tags</h1>
          <p className="text-muted-foreground">Manage tags used to categorize items</p>
        </div>
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogTrigger asChild>
            <Button>
              <Tag className="size-4 mr-2" />
              Add Tag
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Tag</DialogTitle>
              <DialogDescription>Create a new tag to categorize items.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-3 py-2">
              <Label htmlFor="tag-name">Name</Label>
              <Input
                id="tag-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. skincare"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && name.trim()) createMutation.mutate()
                }}
              />
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={createMutation.isPending}>
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton
                loading={createMutation.isPending}
                disabled={!name.trim()}
                onClick={() => createMutation.mutate()}
              >
                Create
              </LoadingButton>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : tags.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center py-12">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Tag className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No tags yet</h3>
          <p className="text-muted-foreground">Add a tag to get started</p>
        </div>
      ) : (
        <DataTable columns={columns} data={tags} />
      )}
    </div>
  )
}
