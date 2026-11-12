"use client"

import * as React from "react"
import {
  Globe,
  Play,
  Search,
  CheckCircle2,
  ListOrdered,
  History,
  Loader2,
  FileText,
  Check,
  ExternalLink,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { toast } from "@/components/ui/sonner"
import {
  crawlerService,
  type CrawlDirectResult,
  type DiscoverResult,
  type QueueResponse,
} from "@/features/crawler"

export default function AdminCrawlerPage() {
  const [activeTab, setActiveTab] = React.useState("direct")

  // --- Tab 1: Direct Crawl State ---
  const [directUrl, setDirectUrl] = React.useState("")
  const [autoIngest, setAutoIngest] = React.useState(true)
  const [autoPublish, setAutoPublish] = React.useState(true)
  const [isCrawlingDirect, setIsCrawlingDirect] = React.useState(false)
  const [directResult, setDirectResult] = React.useState<CrawlDirectResult | null>(null)

  // --- Tab 2: Discovery State ---
  const [discoveryUrl, setDiscoveryUrl] = React.useState("https://daotao.huce.edu.vn/thong-bao")
  const [maxItems, setMaxItems] = React.useState(30)
  const [isDiscovering, setIsDiscovering] = React.useState(false)
  const [discoveryResult, setDiscoveryResult] = React.useState<DiscoverResult | null>(null)
  const [selectedUrls, setSelectedUrls] = React.useState<Set<string>>(new Set())

  // --- Tab 3: Queue State ---
  const [queueData, setQueueData] = React.useState<QueueResponse | null>(null)
  const [isLoadingQueue, setIsLoadingQueue] = React.useState(false)

  // --- Tab 4: Sessions State ---
  const [sessions, setSessions] = React.useState<Array<Record<string, unknown>>>([])
  const [isLoadingSessions, setIsLoadingSessions] = React.useState(false)

  // Load Queue when switching to queue tab
  const loadQueue = React.useCallback(async () => {
    setIsLoadingQueue(true)
    try {
      const data = await crawlerService.getQueue()
      setQueueData(data)
    } catch {
      toast.error("Không thể nạp dữ liệu hàng đợi duyệt")
    } finally {
      setIsLoadingQueue(false)
    }
  }, [])

  // Load Sessions when switching to sessions tab
  const loadSessions = React.useCallback(async () => {
    setIsLoadingSessions(true)
    try {
      const data = await crawlerService.getSessions()
      setSessions(data || [])
    } catch {
      toast.error("Không thể nạp lịch sử phiên crawl")
    } finally {
      setIsLoadingSessions(false)
    }
  }, [])

  // 1. Handle Direct Crawl
  const handleDirectCrawl = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = directUrl.trim()
    if (!trimmed) {
      toast.error("Vui lòng nhập địa chỉ URL bài viết cần crawl")
      return
    }

    setIsCrawlingDirect(true)
    setDirectResult(null)
    try {
      const res = await crawlerService.crawlDirect({
        url: trimmed,
        auto_ingest: autoIngest,
        auto_publish: autoPublish,
      })
      setDirectResult(res)
      toast.success("Crawl URL thành công!", {
        description: `Đã xử lý bài viết: ${res.title || trimmed}`,
      })
    } catch (err) {
      toast.error("Crawl URL thất bại", {
        description: err instanceof Error ? err.message : "Vui lòng kiểm tra lại URL.",
      })
    } finally {
      setIsCrawlingDirect(false)
    }
  }

  // 2. Handle Discovery
  const handleDiscovery = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = discoveryUrl.trim()
    if (!trimmed) {
      toast.error("Vui lòng nhập URL trang danh mục / sitemap")
      return
    }

    setIsDiscovering(true)
    setDiscoveryResult(null)
    setSelectedUrls(new Set())
    try {
      const res = await crawlerService.discover({
        url: trimmed,
        max_items: maxItems,
      })
      setDiscoveryResult(res)
      // Select all by default
      setSelectedUrls(new Set(res.items.map((i) => i.url)))
      toast.success(`Khám phá thành công ${res.total_discovered} liên kết bài viết!`)
    } catch (err) {
      toast.error("Khám phá liên kết thất bại", {
        description: err instanceof Error ? err.message : "Lỗi đọc trang danh mục.",
      })
    } finally {
      setIsDiscovering(false)
    }
  }

  // Toggle selection for discovered URLs
  const toggleSelectUrl = (url: string) => {
    setSelectedUrls((prev) => {
      const next = new Set(prev)
      if (next.has(url)) next.delete(url)
      else next.add(url)
      return next
    })
  }

  // Approve selected URLs into Queue
  const handleApproveSelected = async () => {
    if (!discoveryResult || selectedUrls.size === 0) {
      toast.error("Vui lòng chọn ít nhất một URL để phê duyệt")
      return
    }

    try {
      const res = await crawlerService.approveQueue({
        queue_file: discoveryResult.queue_file,
        approved_urls: Array.from(selectedUrls),
      })
      toast.success(`Đã phê duyệt ${res.total_approved} URL vào hàng đợi cào dữ liệu!`)
    } catch (err) {
      toast.error("Phê duyệt thất bại", {
        description: err instanceof Error ? err.message : "Vui lòng thử lại sau.",
      })
    }
  }

  // Ingest Session into RAG
  const handleIngestSession = async (sessionId: string) => {
    try {
      await crawlerService.ingest({ session_id: sessionId, auto_publish: true })
      toast.success(`Đã nạp toàn bộ phiên "${sessionId}" vào RAG thành công!`)
      loadSessions()
    } catch (err) {
      toast.error("Nạp vào RAG thất bại", {
        description: err instanceof Error ? err.message : "Lỗi xử lý tài liệu.",
      })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h2 className="font-heading text-xl font-bold text-heading">
          Trung tâm Quản trị Content Crawler (Hybrid)
        </h2>
        <p className="text-xs text-muted">
          Thu thập có kiểm soát: Crawl URL trực tiếp, Khám phá liên kết từ danh mục, Hàng đợi phê duyệt
          và Tích hợp RAG Pipeline
        </p>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(val) => {
          setActiveTab(val)
          if (val === "queue") loadQueue()
          if (val === "sessions") loadSessions()
        }}
        className="flex flex-col w-full gap-3"
      >
        <TabsList className="h-9 w-fit bg-surface border border-border p-1">
          <TabsTrigger value="direct" className="gap-1.5 text-xs px-3 py-1 data-active:bg-background data-active:text-heading data-active:shadow-xs data-active:font-semibold">
            <Globe className="h-3.5 w-3.5" />
            <span>Crawl Trực tiếp</span>
          </TabsTrigger>
          <TabsTrigger value="discovery" className="gap-1.5 text-xs px-3 py-1 data-active:bg-background data-active:text-heading data-active:shadow-xs data-active:font-semibold">
            <Search className="h-3.5 w-3.5" />
            <span>Khám phá Liên kết</span>
          </TabsTrigger>
          <TabsTrigger value="queue" className="gap-1.5 text-xs px-3 py-1 data-active:bg-background data-active:text-heading data-active:shadow-xs data-active:font-semibold">
            <ListOrdered className="h-3.5 w-3.5" />
            <span>Hàng đợi Duyệt</span>
          </TabsTrigger>
          <TabsTrigger value="sessions" className="gap-1.5 text-xs px-3 py-1 data-active:bg-background data-active:text-heading data-active:shadow-xs data-active:font-semibold">
            <History className="h-3.5 w-3.5" />
            <span>Lịch sử Phiên Crawl</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Direct Crawl */}
        <TabsContent value="direct" className="space-y-4 pt-3">
          <Card className="border-border shadow-xs">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold text-heading">Crawl Bài viết hoặc Tài liệu Cụ thể</CardTitle>
              <CardDescription className="text-xs">
                Nhập địa chỉ URL bài viết hoặc văn bản cần tải về làm sạch thành Markdown và tải PDF đính kèm.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleDirectCrawl} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-heading">Địa chỉ URL bài viết</label>
                  <Input
                    placeholder="https://daotao.huce.edu.vn/thong-bao/..."
                    value={directUrl}
                    onChange={(e) => setDirectUrl(e.target.value)}
                    className="font-mono text-xs"
                    disabled={isCrawlingDirect}
                  />
                </div>

                <div className="flex flex-wrap items-center gap-6 pt-1 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoIngest}
                      onChange={(e) => setAutoIngest(e.target.checked)}
                      className="rounded border-border"
                    />
                    <span>Tự động nạp vào Document Knowledge Base (Auto-ingest)</span>
                  </label>
                  {autoIngest && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={autoPublish}
                        onChange={(e) => setAutoPublish(e.target.checked)}
                        className="rounded border-border"
                      />
                      <span className="text-emerald-700 font-medium">Băm chunks & Index Vector Qdrant ngay (Auto-publish)</span>
                    </label>
                  )}
                </div>

                <Button
                  type="submit"
                  disabled={isCrawlingDirect}
                  className="bg-brand-primary text-xs text-white hover:bg-brand-primary-hover"
                >
                  {isCrawlingDirect ? (
                    <>
                      <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                      Đang cào dữ liệu & tải tài liệu...
                    </>
                  ) : (
                    <>
                      <Play className="mr-1.5 h-3.5 w-3.5" />
                      Bắt đầu Crawl Ngay
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {directResult && (
            <Card className="border-border bg-brand-primary/5 shadow-xs">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                    <CardTitle className="text-sm font-bold text-heading">Kết quả Crawl Thành công</CardTitle>
                  </div>
                  <Badge variant="outline" className="border-emerald-500/30 bg-emerald-100 text-emerald-800 text-[11px]">
                    {directResult.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                <div>
                  <span className="font-semibold text-heading">Tiêu đề trích xuất:</span>{" "}
                  <span className="text-brand-primary font-medium">{directResult.title || "—"}</span>
                </div>
                <div>
                  <span className="font-semibold text-heading">Độ dài Markdown:</span>{" "}
                  <span>{directResult.content_length.toLocaleString()} ký tự</span>
                </div>
                <div>
                  <span className="font-semibold text-heading">Tài liệu đính kèm (PDF/Ảnh):</span>{" "}
                  <span>{directResult.media_count} tệp tin</span>
                </div>
                <div>
                  <span className="font-semibold text-heading">Trạng thái RAG Ingestion:</span>{" "}
                  <Badge variant="outline" className={directResult.ingested ? "text-emerald-700 bg-emerald-50 ml-1" : "text-muted ml-1"}>
                    {directResult.ingested ? "Đã nạp vào RAG & Vector Index" : "Chưa nạp (chỉ lưu Crawl Artifacts)"}
                  </Badge>
                </div>
                {directResult.page_dir && (
                  <p className="font-mono text-[11px] text-muted truncate">Thư mục Artifact: {directResult.page_dir}</p>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Tab 2: Discovery */}
        <TabsContent value="discovery" className="space-y-4 pt-3">
          <Card className="border-border shadow-xs">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold text-heading">Khám phá Liên kết từ Trang Danh mục / Sitemap</CardTitle>
              <CardDescription className="text-xs">
                Trích xuất danh sách các bài viết tiềm năng mà không tự động tải nội dung, sẵn sàng đưa vào hàng đợi phê duyệt.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleDiscovery} className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="flex-1 space-y-1.5">
                  <label className="text-xs font-medium text-heading">Địa chỉ trang danh mục / Sitemap / RSS</label>
                  <Input
                    placeholder="https://daotao.huce.edu.vn/thong-bao"
                    value={discoveryUrl}
                    onChange={(e) => setDiscoveryUrl(e.target.value)}
                    className="font-mono text-xs"
                    disabled={isDiscovering}
                  />
                </div>
                <div className="w-28 space-y-1.5">
                  <label className="text-xs font-medium text-heading">Giới hạn</label>
                  <Input
                    type="number"
                    min={1}
                    max={200}
                    value={maxItems}
                    onChange={(e) => setMaxItems(Number(e.target.value))}
                    className="text-xs"
                    disabled={isDiscovering}
                  />
                </div>
                <Button
                  type="submit"
                  disabled={isDiscovering}
                  className="bg-brand-primary text-xs text-white hover:bg-brand-primary-hover"
                >
                  {isDiscovering ? (
                    <>
                      <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                      Đang quét liên kết...
                    </>
                  ) : (
                    <>
                      <Search className="mr-1.5 h-3.5 w-3.5" />
                      Khám phá
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {discoveryResult && (
            <Card className="border-border shadow-xs">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <div>
                  <CardTitle className="text-sm font-bold text-heading">
                    Liên kết phát hiện ({discoveryResult.total_discovered} bài viết)
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Nguồn: {discoveryResult.source_url} ({discoveryResult.source_type})
                  </CardDescription>
                </div>
                <Button
                  onClick={handleApproveSelected}
                  disabled={selectedUrls.size === 0}
                  className="bg-emerald-600 text-xs text-white hover:bg-emerald-700"
                >
                  <Check className="mr-1.5 h-3.5 w-3.5" />
                  Phê duyệt {selectedUrls.size} URL đã chọn
                </Button>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12 text-center">
                        <input
                          type="checkbox"
                          checked={selectedUrls.size === discoveryResult.items.length && discoveryResult.items.length > 0}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedUrls(new Set(discoveryResult.items.map((i) => i.url)))
                            } else {
                              setSelectedUrls(new Set())
                            }
                          }}
                        />
                      </TableHead>
                      <TableHead>Tiêu đề bài viết</TableHead>
                      <TableHead>Địa chỉ URL</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {discoveryResult.items.map((item, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="w-12 text-center">
                          <input
                            type="checkbox"
                            checked={selectedUrls.has(item.url)}
                            onChange={() => toggleSelectUrl(item.url)}
                          />
                        </TableCell>
                        <TableCell className="text-xs font-medium text-heading">
                          {item.title || "—"}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted max-w-md truncate">
                          <a href={item.url} target="_blank" rel="noopener noreferrer" className="hover:underline flex items-center gap-1">
                            <span>{item.url}</span>
                            <ExternalLink className="h-3 w-3 shrink-0" />
                          </a>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Tab 3: Queue */}
        <TabsContent value="queue" className="space-y-4 pt-3">
          <Card className="border-border shadow-xs">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-sm font-bold text-heading">Hàng đợi Phê duyệt (Review Queue)</CardTitle>
                <CardDescription className="text-xs">
                  Danh sách URL đã được phê duyệt sẵn sàng nạp vào crawler execution batch.
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={loadQueue}
                disabled={isLoadingQueue}
                className="text-xs"
              >
                {isLoadingQueue ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Làm mới"}
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg border border-border bg-surface/50 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold text-heading">Số lượng URL Đã Phê duyệt (Approved)</p>
                    <p className="text-2xl font-bold text-brand-primary">{queueData?.approved_total ?? 0}</p>
                  </div>
                  <Badge variant="outline" className="border-emerald-500/30 bg-emerald-50 text-emerald-700 text-xs">
                    Sẵn sàng Crawl
                  </Badge>
                </div>
              </div>

              {queueData?.approved_urls && queueData.approved_urls.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-heading">Danh sách URL trong hàng đợi:</p>
                  <div className="max-h-60 overflow-y-auto rounded-lg border border-border bg-surface p-2 text-xs font-mono space-y-1">
                    {queueData.approved_urls.map((url, i) => (
                      <div key={i} className="truncate p-1 hover:bg-muted/50 rounded">
                        {url}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {queueData?.discovered_files && queueData.discovered_files.length > 0 && (
                <div className="space-y-2 pt-2">
                  <p className="text-xs font-semibold text-heading">Tệp tin Discovery đã lưu gần đây:</p>
                  <div className="space-y-1.5 text-xs">
                    {queueData.discovered_files.map((df, idx) => (
                      <div key={idx} className="flex items-center justify-between rounded border border-border/70 p-2.5">
                        <div>
                          <p className="font-mono font-medium text-heading">{df.filename}</p>
                          <p className="text-[11px] text-muted">{df.source_url} • {df.total} bài viết</p>
                        </div>
                        <Badge variant="secondary" className="text-[10px]">
                          {df.total} items
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Sessions */}
        <TabsContent value="sessions" className="space-y-4 pt-3">
          <Card className="border-border shadow-xs">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-sm font-bold text-heading">Lịch sử Phiên Crawl</CardTitle>
                <CardDescription className="text-xs">
                  Nhật ký các phiên cào dữ liệu trước đây và trạng thái Ingestion vào RAG.
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={loadSessions}
                disabled={isLoadingSessions}
                className="text-xs"
              >
                {isLoadingSessions ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Làm mới"}
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Mã phiên (Session ID)</TableHead>
                    <TableHead>Thời gian</TableHead>
                    <TableHead>Tổng URL</TableHead>
                    <TableHead>Thành công</TableHead>
                    <TableHead className="text-right">Hành động</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="h-24 text-center text-xs text-muted">
                        Chưa có phiên crawl nào được ghi nhận.
                      </TableCell>
                    </TableRow>
                  ) : (
                    sessions.map((s, idx) => {
                      const sid = String(s.session_id || s.id || `session-${idx}`)
                      const total = Number(s.total_urls ?? s.total ?? 0)
                      const succ = Number(s.succeeded ?? s.success_count ?? 0)
                      const started = String(s.started_at || s.created_at || "—")

                      return (
                        <TableRow key={idx}>
                          <TableCell className="font-mono text-xs font-semibold text-heading">
                            {sid}
                          </TableCell>
                          <TableCell className="text-xs text-muted">{started}</TableCell>
                          <TableCell className="text-xs">{total}</TableCell>
                          <TableCell className="text-xs text-emerald-600 font-medium">
                            {succ}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleIngestSession(sid)}
                              className="h-7 text-xs gap-1 border-brand-primary/40 text-brand-primary hover:bg-brand-primary/10"
                            >
                              <FileText className="h-3 w-3" />
                              <span>Nạp RAG</span>
                            </Button>
                          </TableCell>
                        </TableRow>
                      )
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
