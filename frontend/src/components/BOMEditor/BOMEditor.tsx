import { useState, useMemo, useEffect, useRef, type CSSProperties } from "react";
import {
  useProjectBOM,
  useTriggerBOMExtraction,
  useUpdateBOMLineItem,
  useAddBOMLineItem,
  useDeleteBOMLineItem,
} from "../../hooks/useApi";
import {
  exportBOMCSV,
  exportBOMPDF,
  type BOMLineItem,
  type BOMLineItemUpdatePayload,
  type EquipmentCatalogItem,
  type BOMLineItemCreatePayload,
} from "../../api/client";
import BOMCategoryGroup from "./BOMCategoryGroup";
import BOMTotalsBar from "./BOMTotalsBar";
import CatalogSearchModal from "./CatalogSearchModal";
import ExportMenu from "./ExportMenu";
import BOMChat from "./BOMChat";
import { useGridNavigation } from "./useGridNavigation";

interface Props {
  projectId: string;
  projectStatus: string;
}

const CATEGORY_ORDER = [
  "panel", "inverter", "racking", "electrical",
  "battery", "labor", "permit", "other",
];

const toolbarStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  marginBottom: 16,
  flexWrap: "wrap",
};

const thStyle: CSSProperties = {
  padding: "6px 8px",
  textAlign: "left",
  fontSize: 12,
  fontWeight: 600,
  color: "#1a237e",
  background: "#e8eaf6",
  borderBottom: "1px solid #c5cae9",
  position: "sticky",
  top: 0,
  zIndex: 2,
};

const chatToggleStyle: CSSProperties = {
  background: "#1a237e",
  color: "#fff",
  border: "none",
  borderRadius: 6,
  padding: "8px 14px",
  fontSize: 13,
  cursor: "pointer",
  fontWeight: 500,
};

export default function BOMEditor({ projectId, projectStatus }: Props) {
  const { data: extraction, isLoading } = useProjectBOM(projectId);
  const triggerExtraction = useTriggerBOMExtraction();
  const updateItem = useUpdateBOMLineItem();
  const addItem = useAddBOMLineItem();
  const deleteItem = useDeleteBOMLineItem();

  const [taxRate, setTaxRate] = useState(0.085);
  const [markupPct, setMarkupPct] = useState(0.15);
  const [showCatalog, setShowCatalog] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());

  const tableRef = useRef<HTMLDivElement>(null);

  const lineItems = extraction?.line_items ?? [];

  // Group items by category
  const grouped = useMemo(() => {
    const groups: Record<string, BOMLineItem[]> = {};
    for (const item of lineItems) {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    }
    return CATEGORY_ORDER
      .filter((cat) => groups[cat]?.length)
      .map((cat) => ({ category: cat, items: groups[cat] }));
  }, [lineItems]);

  // Flat list of visible item IDs (excluding collapsed categories)
  const flatVisibleItems = useMemo(() => {
    return grouped
      .filter((g) => !collapsedCategories.has(g.category))
      .flatMap((g) => g.items.map((item) => item.id));
  }, [grouped, collapsedCategories]);

  // Map of item ID → item for quick lookups
  const itemsById = useMemo(() => {
    const map = new Map<string, BOMLineItem>();
    for (const item of lineItems) {
      map.set(item.id, item);
    }
    return map;
  }, [lineItems]);

  // Calculate totals client-side for instant feedback
  const subtotal = lineItems.reduce((sum, i) => sum + i.quantity * i.unit_cost, 0);
  const taxAmount = subtotal * taxRate;
  const markupAmount = subtotal * markupPct;
  const grandTotal = subtotal + taxAmount + markupAmount;

  const handleUpdate = (itemId: string, payload: BOMLineItemUpdatePayload) => {
    updateItem.mutate({ itemId, payload });
  };

  const handleDelete = (itemId: string) => {
    deleteItem.mutate(itemId);
  };

  // Grid navigation hook
  const grid = useGridNavigation({
    flatVisibleItems,
    itemsById,
    onSave: handleUpdate,
    onDelete: handleDelete,
  });

  // Click-outside handler: commit edit and deselect
  const commitEditRef = useRef(grid.commitEdit);
  commitEditRef.current = grid.commitEdit;
  const selectCellRef = useRef(grid.selectCell);
  selectCellRef.current = grid.selectCell;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (tableRef.current && !tableRef.current.contains(e.target as Node)) {
        commitEditRef.current();
        selectCellRef.current(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggleCollapse = (category: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  };

  const handleCatalogSelect = (catalogItem: EquipmentCatalogItem) => {
    addItem.mutate({
      projectId,
      payload: {
        catalog_item_id: catalogItem.id,
        category: catalogItem.category,
        name: catalogItem.name,
        description: catalogItem.description ?? undefined,
        specifications: catalogItem.specifications ?? undefined,
        quantity: 1,
        unit: catalogItem.unit,
        unit_cost: catalogItem.unit_cost,
      },
    });
    setShowCatalog(false);
  };

  const handleAddManual = () => {
    addItem.mutate({
      projectId,
      payload: {
        category: "other",
        name: "New Item",
        quantity: 1,
        unit: "ea",
        unit_cost: 0,
      },
    });
  };

  const handleChatAddItem = (payload: BOMLineItemCreatePayload) => {
    addItem.mutate({ projectId, payload });
  };

  const handleChatUpdateItem = (itemId: string, payload: BOMLineItemUpdatePayload) => {
    updateItem.mutate({ itemId, payload });
  };

  const handleChatDeleteItem = (itemId: string) => {
    deleteItem.mutate(itemId);
  };

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const blob = await exportBOMCSV(projectId, taxRate, markupPct);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bom-${projectId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const handleExportPDF = async () => {
    setExporting(true);
    try {
      const blob = await exportBOMPDF(projectId, taxRate, markupPct);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `proposal-${projectId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  // No extraction yet — show trigger button
  if (!isLoading && !extraction) {
    const canExtract = projectStatus === "completed";
    return (
      <div style={{ textAlign: "center", padding: 40 }}>
        <p style={{ fontSize: 16, color: "#666", marginBottom: 16 }}>
          {canExtract
            ? "No BOM extraction yet. Extract equipment and materials from the classified sheets."
            : "Classification must complete before BOM extraction."}
        </p>
        <button
          onClick={() => triggerExtraction.mutate(projectId)}
          disabled={!canExtract || triggerExtraction.isPending}
          style={{
            background: canExtract ? "#f9a825" : "#ccc",
            color: canExtract ? "#000" : "#666",
            border: "none",
            borderRadius: 6,
            padding: "12px 24px",
            fontSize: 15,
            fontWeight: 600,
            cursor: canExtract ? "pointer" : "not-allowed",
          }}
        >
          {triggerExtraction.isPending ? "Starting..." : "Extract BOM"}
        </button>
      </div>
    );
  }

  // Extraction in progress
  if (extraction && (extraction.status === "pending" || extraction.status === "extracting")) {
    return (
      <div style={{ textAlign: "center", padding: 40 }}>
        <div
          style={{
            width: 40,
            height: 40,
            border: "4px solid #e0e0e0",
            borderTopColor: "#f9a825",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            margin: "0 auto 16px",
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <p style={{ fontSize: 16, color: "#666" }}>
          Extracting BOM from classified sheets...
        </p>
        <p style={{ fontSize: 13, color: "#999" }}>
          This uses AI to read equipment schedules, single-line diagrams, and more.
          Auto-refreshing every 3 seconds.
        </p>
      </div>
    );
  }

  // Extraction failed
  if (extraction?.status === "failed") {
    return (
      <div style={{ textAlign: "center", padding: 40 }}>
        <p style={{ color: "#f44336", fontSize: 16, marginBottom: 16 }}>
          BOM extraction failed.
        </p>
        <button
          onClick={() => triggerExtraction.mutate(projectId)}
          disabled={triggerExtraction.isPending}
          style={{
            background: "#f9a825",
            color: "#000",
            border: "none",
            borderRadius: 6,
            padding: "10px 20px",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {triggerExtraction.isPending ? "Starting..." : "Retry Extraction"}
        </button>
      </div>
    );
  }

  // BOM Editor with optional chat panel
  return (
    <div style={{ display: "flex", height: "calc(100vh - 200px)" }}>
      {/* Main BOM Table */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Toolbar */}
        <div style={toolbarStyle}>
          <button
            onClick={handleAddManual}
            style={{
              background: "#fff",
              border: "1px solid #ddd",
              borderRadius: 6,
              padding: "8px 14px",
              fontSize: 13,
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            + Add Item
          </button>
          <button
            onClick={() => setShowCatalog(true)}
            style={{
              background: "#fff",
              border: "1px solid #ddd",
              borderRadius: 6,
              padding: "8px 14px",
              fontSize: 13,
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            Search Catalog
          </button>
          <button
            onClick={() => triggerExtraction.mutate(projectId)}
            disabled={triggerExtraction.isPending}
            style={{
              background: "#fff",
              border: "1px solid #ddd",
              borderRadius: 6,
              padding: "8px 14px",
              fontSize: 13,
              cursor: "pointer",
              fontWeight: 500,
              opacity: triggerExtraction.isPending ? 0.5 : 1,
            }}
          >
            {triggerExtraction.isPending ? "Re-extracting..." : "Re-extract"}
          </button>
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 13, color: "#999" }}>
            {lineItems.length} items
          </span>
          <button
            onClick={() => setShowChat(!showChat)}
            style={{
              ...chatToggleStyle,
              background: showChat ? "#283593" : "#1a237e",
            }}
          >
            {showChat ? "Close AI" : "AI Assistant"}
          </button>
          <ExportMenu
            onExportCSV={handleExportCSV}
            onExportPDF={handleExportPDF}
            exporting={exporting}
          />
        </div>

        {/* BOM Table — grid container */}
        <div
          ref={tableRef}
          style={{
            background: "#fff",
            borderRadius: "8px 8px 0 0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            overflow: "auto",
            flex: 1,
            outline: "none",
          }}
          onKeyDown={grid.handleKeyDown}
          tabIndex={0}
          role="grid"
        >
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ ...thStyle, width: 36, textAlign: "center" }}>#</th>
                <th style={{ ...thStyle, width: "30%" }}>Item</th>
                <th style={{ ...thStyle, width: "15%" }}>Specs</th>
                <th style={{ ...thStyle, width: "8%", textAlign: "center" }}>Qty</th>
                <th style={{ ...thStyle, width: "7%", textAlign: "center" }}>Unit</th>
                <th style={{ ...thStyle, width: "12%", textAlign: "right" }}>$/Unit</th>
                <th style={{ ...thStyle, width: "14%", textAlign: "right" }}>Total</th>
                <th style={{ ...thStyle, width: 36 }}></th>
              </tr>
            </thead>
            <tbody>
              {grouped.map((group) => (
                <BOMCategoryGroup
                  key={group.category}
                  category={group.category}
                  items={group.items}
                  collapsed={collapsedCategories.has(group.category)}
                  onToggleCollapse={toggleCollapse}
                  selectedCell={grid.selectedCell}
                  isEditing={grid.isEditing}
                  editValue={grid.editValue}
                  saveStatus={grid.saveStatus}
                  onSelectCell={grid.selectCell}
                  onStartEditing={grid.startEditing}
                  onEditValueChange={grid.setEditValue}
                  onDelete={handleDelete}
                />
              ))}
              {lineItems.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: "center", padding: 40, color: "#999" }}>
                    No line items. Add items manually or from the catalog.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Totals Bar */}
        <BOMTotalsBar
          subtotal={subtotal}
          taxRate={taxRate}
          taxAmount={taxAmount}
          markupPct={markupPct}
          markupAmount={markupAmount}
          grandTotal={grandTotal}
          onTaxRateChange={setTaxRate}
          onMarkupPctChange={setMarkupPct}
        />
      </div>

      {/* Chat Panel */}
      {showChat && (
        <BOMChat
          projectId={projectId}
          onAddItem={handleChatAddItem}
          onUpdateItem={handleChatUpdateItem}
          onDeleteItem={handleChatDeleteItem}
          onClose={() => setShowChat(false)}
        />
      )}

      {/* Catalog Search Modal */}
      {showCatalog && (
        <CatalogSearchModal
          onSelect={handleCatalogSelect}
          onClose={() => setShowCatalog(false)}
        />
      )}
    </div>
  );
}
