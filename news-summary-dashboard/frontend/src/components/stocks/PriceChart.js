import React from "react";
import { Line } from "react-chartjs-2";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from "chart.js";
import "chartjs-adapter-date-fns";
import { Box, useColorModeValue } from "@chakra-ui/react";

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

const PriceChart = ({ chartData, timeRange, showPrediction = false }) => {
    const cardBg = useColorModeValue("white", "#131722");
    const textColor = useColorModeValue("gray.600", "#D1D4DC");
    const gridColor = useColorModeValue(
        "rgba(0, 0, 0, 0.05)",
        "rgba(255, 255, 255, 0.05)"
    );

    if (!chartData || !chartData.rawData) {
        return null;
    }

    const processStockData = (rawData) => {
        const historical = { labels: [], data: [] };
        const predicted = { labels: [], data: [] };

        rawData.forEach((item) => {
        const date = new Date(item.date);
        const dayOfWeek = date.getDay();
        if (dayOfWeek !== 0 && dayOfWeek !== 6) {
            // Skip weekends
            if (item.close_price !== undefined) {
            historical.labels.push(item.date);
            historical.data.push(item.close_price);
            }
            if (item.predict_price !== undefined) {
            predicted.labels.push(item.date);
            predicted.data.push(item.predict_price);
            }
        }
        });
        return { historical, predicted };
    };

    const shouldShowPrediction = showPrediction && (timeRange === "1M" || timeRange === "3M");
    const { historical, predicted } = processStockData(chartData.rawData);

    // *** NEW LOGIC TO MERGE TIME AXIS ***
    // Adjust time axis based on whether prediction is shown
    let allUniqueLabels;
    
    if (shouldShowPrediction && predicted.labels.length > 0) {
        // If showing prediction, include both historical and predicted data
        allUniqueLabels = [
            ...new Set([...historical.labels, ...predicted.labels]),
        ];
    } else {
        // If not showing prediction, only show historical data
        allUniqueLabels = [...historical.labels];
    }

    // 2. Sort the list of dates in chronological order
    allUniqueLabels.sort((a, b) => new Date(a) - new Date(b));

    // 3. Create Map for fast value lookup
    const historicalDataMap = new Map(
        historical.labels.map((label, i) => [label, historical.data[i]])
    );
    const predictedDataMap = new Map(
        predicted.labels.map((label, i) => [label, predicted.data[i]])
    );

    // 4. Create final data arrays, map values to merged time axis
    // If no value for a day, fill with `null`
    const finalHistoricalData = allUniqueLabels.map(
        (label) => historicalDataMap.get(label) || null
    );
    const finalPredictedData = allUniqueLabels.map(
        (label) => predictedDataMap.get(label) || null
    );

    const datasets = [];

    // Dataset for predicted data
    if (shouldShowPrediction && predicted.data.length > 0) {
        datasets.push({
        label: "Predicted Price",
        data: finalPredictedData,
        fill: true,
        borderColor: "rgb(255, 99, 132)",
        backgroundColor: "rgba(255, 99, 132, 0.2)",
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.4, // Make the curve smoother
        borderDash: [5, 5],
        spanGaps: true, // Connect data points with `null` in between
        });
    }

    // Dataset for historical data
    if (historical.data.length > 0) {
        datasets.push({
        label: shouldShowPrediction ? "Actual Price" : "Stock Price",
        data: finalHistoricalData,
        fill: true,
        borderColor: "rgb(54, 162, 235)",
        backgroundColor: "rgba(54, 162, 235, 0.2)",
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.4,
        spanGaps: true,
        });
    }

    const data = {
        labels: allUniqueLabels, // Use the merged and sorted time axis
        datasets: datasets,
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
        x: {
            type: "category",
            ticks: {
            color: textColor,
            callback: function (value, index) {
                const label = this.getLabelForValue(value);
                const date = new Date(label);
                return date.toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                });
            },
            maxRotation: 0, // Prevent label rotation
            autoSkip: true, // Automatically skip labels if too dense
            maxTicksLimit: 10, // Limit number of labels
            },
            grid: { display: false },
        },
        y: {
            ticks: { color: textColor },
            grid: { color: gridColor, drawBorder: false },
        },
        },
        plugins: {
        legend: {
            display: shouldShowPrediction,
            labels: { color: textColor, usePointStyle: true, padding: 20 },
        },
        tooltip: {
            mode: "index",
            intersect: false,
            callbacks: {
            title: (context) =>
                new Date(context[0].label).toLocaleDateString("en-US"),
            label: (context) =>
                `${context.dataset.label}: ${context.parsed.y.toLocaleString(
                "en-US"
                )} VND`,
            },
        },
        },
        interaction: { intersect: false, mode: "index" },
    };

    return (
        <Box p={4} bg={cardBg} mt={6} minH="500px" borderRadius="lg">
        <Line options={options} data={data} />
        </Box>
    );
};

export default PriceChart;
