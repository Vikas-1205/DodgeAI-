import { useRef, useEffect, useCallback, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const NODE_COLORS = {
    Customer: '#6c7bea',
    Product: '#4cce8a',
    Order: '#e8a44c',
    OrderItem: '#8b9dc3',
    Delivery: '#5cc8e8',
    Invoice: '#e85ca4',
    Payment: '#c85ce8',
};

const NODE_SIZES = {
    Customer: 7, Product: 6, Order: 8,
    OrderItem: 4, Delivery: 6, Invoice: 6, Payment: 6,
};

const LEGEND = [
    { type: 'Customer', color: NODE_COLORS.Customer },
    { type: 'Product', color: NODE_COLORS.Product },
    { type: 'Order', color: NODE_COLORS.Order },
    { type: 'Delivery', color: NODE_COLORS.Delivery },
    { type: 'Invoice', color: NODE_COLORS.Invoice },
    { type: 'Payment', color: NODE_COLORS.Payment },
];

export default function GraphPanel({ graphData, highlightNodes }) {
    const fgRef = useRef();
    const containerRef = useRef();
    const [hoverNode, setHoverNode] = useState(null);

    const highlightSet = useMemo(() => new Set(highlightNodes || []), [highlightNodes]);

    // Track neighbors of the hovered node
    const neighbors = useMemo(() => {
        if (!hoverNode) return new Set();
        const set = new Set();
        graphData.links.forEach(link => {
            const src = typeof link.source === 'object' ? link.source.id : link.source;
            const tgt = typeof link.target === 'object' ? link.target.id : link.target;
            if (src === hoverNode.id) set.add(tgt);
            if (tgt === hoverNode.id) set.add(src);
        });
        return set;
    }, [hoverNode, graphData.links]);

    /* Auto-fit on first load and force tuning */
    useEffect(() => {
        if (fgRef.current && graphData.nodes.length > 0) {
            // Increase repulsion
            fgRef.current.d3Force('charge').strength(-150);
            fgRef.current.d3Force('link').distance(70);

            setTimeout(() => fgRef.current.zoomToFit(400, 80), 500);
        }
    }, [graphData]);

    /* Canvas node painter */
    const paintNode = useCallback((node, ctx, globalScale) => {
        const isHighlighted = highlightSet.has(node.id);
        const isHovered = hoverNode && node.id === hoverNode.id;
        const isNeighbor = neighbors.has(node.id);
        const isActive = isHighlighted || isHovered || isNeighbor;
        const isDimmed = (hoverNode || highlightSet.size > 0) && !isActive;

        const baseSize = NODE_SIZES[node.type] || 5;
        let size = baseSize;
        if (isHighlighted) size *= 1.6;
        if (isHovered) size *= 1.3;

        const color = NODE_COLORS[node.type] || '#888';

        /* Glow ring for active nodes */
        if (isActive) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
            ctx.fillStyle = `${color}22`;
            ctx.fill();

            ctx.beginPath();
            ctx.arc(node.x, node.y, size + 2, 0, 2 * Math.PI);
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }

        /* Node circle with border */
        ctx.beginPath();
        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
        ctx.fillStyle = isDimmed ? `${color}44` : (isHighlighted || isHovered ? color : `${color}bb`);
        ctx.fill();

        // Node border for visibility
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 0.5;
        ctx.stroke();

        /* Label */
        const fontSize = isActive ? 13 / globalScale : 10 / globalScale;
        if (globalScale > 0.8 || isActive) {
            ctx.font = `${isActive ? '600 ' : ''}${fontSize}px Inter, sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillStyle = isDimmed ? '#9fa4b444' : (isActive ? '#fff' : '#9fa4b4');

            // Label background for better contrast when hovered/active
            if (isActive) {
                const text = node.label || '';
                const textWidth = ctx.measureText(text).width;
                ctx.fillStyle = 'rgba(15, 17, 23, 0.7)';
                ctx.fillRect(node.x - textWidth / 2 - 2, node.y + size + 2, textWidth + 4, fontSize + 2);
            }

            ctx.fillStyle = isActive ? '#fff' : (isDimmed ? '#9fa4b444' : '#9fa4b4');
            ctx.fillText(node.label || '', node.x, node.y + size + 3);
        }
    }, [highlightSet, hoverNode, neighbors]);

    /* Link styling */
    const linkColor = useCallback((link) => {
        const src = typeof link.source === 'object' ? link.source.id : link.source;
        const tgt = typeof link.target === 'object' ? link.target.id : link.target;
        const isActive = (highlightSet.has(src) && highlightSet.has(tgt)) ||
                        (hoverNode && (src === hoverNode.id || tgt === hoverNode.id));
        const isDimmed = (hoverNode || highlightSet.size > 0) && !isActive;

        if (isActive) return '#6c7beaaa';
        return isDimmed ? '#2e334811' : '#2e334855';
    }, [highlightSet, hoverNode]);

    const linkWidth = useCallback((link) => {
        const src = typeof link.source === 'object' ? link.source.id : link.source;
        const tgt = typeof link.target === 'object' ? link.target.id : link.target;
        if (highlightSet.has(src) && highlightSet.has(tgt)) return 2.5;
        if (hoverNode && (src === hoverNode.id || tgt === hoverNode.id)) return 1.5;
        return 0.5;
    }, [highlightSet, hoverNode]);

    return (
        <div className="graph-panel">
            <div className="graph-panel__header">
                <span className="graph-panel__title">Knowledge Graph</span>
                <span className="graph-panel__stats">
                    {graphData.nodes.length} nodes · {graphData.links.length} edges
                </span>
            </div>

            <div className="graph-panel__canvas" ref={containerRef}>
                {graphData.nodes.length > 0 ? (
                    <ForceGraph2D
                        ref={fgRef}
                        graphData={graphData}
                        nodeCanvasObject={paintNode}
                        onNodeHover={setHoverNode}
                        nodePointerAreaPaint={(node, color, ctx) => {
                            const size = NODE_SIZES[node.type] || 5;
                            ctx.beginPath();
                            ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
                            ctx.fillStyle = color;
                            ctx.fill();
                        }}
                        linkColor={linkColor}
                        linkWidth={linkWidth}
                        linkDirectionalParticles={link => (highlightSet.has(link.source?.id) && highlightSet.has(link.target?.id)) || (hoverNode && (link.source?.id === hoverNode.id || link.target?.id === hoverNode.id)) ? 4 : 0}
                        linkDirectionalParticleWidth={2}
                        linkDirectionalParticleSpeed={0.005}
                        linkDirectionalParticleColor={() => '#6c7bea'}
                        linkDirectionalArrowLength={3}
                        linkDirectionalArrowRelPos={0.85}
                        linkDirectionalArrowColor={linkColor}
                        d3AlphaDecay={0.03}
                        d3VelocityDecay={0.2}
                        cooldownTicks={100}
                        backgroundColor="#0f1117"
                        width={containerRef.current?.clientWidth}
                        height={containerRef.current?.clientHeight}
                    />
                ) : (
                    <div className="welcome">
                        <div className="welcome__icon">📊</div>
                        <div className="welcome__title">Loading graph...</div>
                    </div>
                )}
            </div>

            <div className="graph-panel__legend">
                {LEGEND.map(({ type, color }) => (
                    <div className="legend-item" key={type}>
                        <span className="legend-dot" style={{ background: color }} />
                        {type}
                    </div>
                ))}
            </div>
        </div>
    );
}
