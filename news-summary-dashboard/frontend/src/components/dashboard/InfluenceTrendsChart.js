import React from "react";
import {
  Box,
  Heading,
  useColorModeValue
} from "@chakra-ui/react";

const data = [62, 63, 81, 48, 55, 67, 72];
const width = 500;
const height = 200;
const paddingX = 40;
const paddingY = 30;
const chartW = width - 2 * paddingX;
const chartH = height - 2 * paddingY;

// Tính điểm
const points = data.map((v, i) => [
  paddingX + (i * chartW) / (data.length - 1),
  paddingY + chartH - ((v - Math.min(...data)) * chartH) / (Math.max(...data) - Math.min(...data)),
]);

// Hàm tạo đường cong mượt (Cubic Bezier)
function getSmoothPath(pts) {
  let d = "";
  for (let i = 0; i < pts.length; i++) {
    const [x, y] = pts[i];
    if (i === 0) {
      d = `M${x},${y}`;
    } else {
      const [px, py] = pts[i - 1];
      const c1x = px + (x - px) / 2;
      const c1y = py;
      const c2x = px + (x - px) / 2;
      const c2y = y;
      d += ` C${c1x},${c1y} ${c2x},${c2y} ${x},${y}`;
    }
  }
  return d;
}

const gridCount = 5;
const gridYs = Array.from({ length: gridCount }, (_, i) =>
  paddingY + (i * chartH) / (gridCount - 1)
);

const InfluenceTrendsChart = () => {
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const gridColor = useColorModeValue("gray.100", "gray.700");
  const lineColor = "blue.400";
  const textColor = useColorModeValue("gray.600", "gray.400");

  const maxValue = Math.max(...data);
  const minValue = Math.min(...data);
  const valueRange = maxValue - minValue;

  return (
    <Box
      p={6}
      bg={bgColor}
      borderRadius="lg"
      borderWidth="1px"
      borderColor={borderColor}
      flex="1"
    >
      <Heading size="md" mb={6}>Influence Trends</Heading>
      <Box w="100%" h="200px" position="relative">
        <svg width={width} height={height} style={{ width: "100%", height: "200px" }}>
          {/* Grid lines and labels */}
          {gridYs.map((y, i) => {
            const value = Math.round(maxValue - (i * valueRange) / (gridCount - 1));
            return (
              <g key={i}>
                <line
                  x1={paddingX}
                  x2={width - paddingX}
                  y1={y}
                  y2={y}
                  stroke={gridColor}
                  strokeWidth={1}
                  strokeDasharray="4,4"
                />
                <text
                  x={paddingX - 10}
                  y={y}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fill={textColor}
                  fontSize="12"
                >
                  {value}
                </text>
              </g>
            );
          })}

          {/* X-axis labels */}
          {data.map((_, i) => (
            <text
              key={i}
              x={paddingX + (i * chartW) / (data.length - 1)}
              y={height - paddingY + 20}
              textAnchor="middle"
              fill={textColor}
              fontSize="12"
            >
              {`Day ${i + 1}`}
            </text>
          ))}

          {/* Area under the curve */}
          <path
            d={`${getSmoothPath(points)} L${width - paddingX},${height - paddingY} L${paddingX},${height - paddingY} Z`}
            fill={lineColor}
            fillOpacity="0.1"
          />

          {/* Smooth line */}
          <path
            d={getSmoothPath(points)}
            fill="none"
            stroke={lineColor}
            strokeWidth={2.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* Dots */}
          {points.map(([x, y], i) => (
            <g key={i}>
              <circle
                cx={x}
                cy={y}
                r={4}
                fill={bgColor}
                stroke={lineColor}
                strokeWidth={2.5}
              />
              <circle
                cx={x}
                cy={y}
                r={12}
                fill="transparent"
                stroke="transparent"
                onMouseOver={(e) => {
                  const circle = e.target.previousSibling;
                  circle.setAttribute('r', '6');
                }}
                onMouseOut={(e) => {
                  const circle = e.target.previousSibling;
                  circle.setAttribute('r', '4');
                }}
              />
            </g>
          ))}
        </svg>
      </Box>
    </Box>
  );
};

export default InfluenceTrendsChart; 