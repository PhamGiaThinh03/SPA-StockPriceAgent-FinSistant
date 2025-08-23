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
            // Bỏ qua cuối tuần
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

    // *** LOGIC MỚI ĐỂ HỢP NHẤT TRỤC THỜI GIAN ***
    // Điều chỉnh trục thời gian dựa trên việc có hiển thị prediction hay không
    let allUniqueLabels;
    
    if (shouldShowPrediction && predicted.labels.length > 0) {
        // Nếu hiển thị prediction, bao gồm cả dữ liệu lịch sử và dự đoán
        allUniqueLabels = [
            ...new Set([...historical.labels, ...predicted.labels]),
        ];
    } else {
        // Nếu không hiển thị prediction, chỉ hiển thị dữ liệu lịch sử
        allUniqueLabels = [...historical.labels];
    }

    // 2. Sắp xếp danh sách các ngày này theo đúng thứ tự thời gian
    allUniqueLabels.sort((a, b) => new Date(a) - new Date(b));

    // 3. Tạo Map để tra cứu giá trị nhanh chóng
    const historicalDataMap = new Map(
        historical.labels.map((label, i) => [label, historical.data[i]])
    );
    const predictedDataMap = new Map(
        predicted.labels.map((label, i) => [label, predicted.data[i]])
    );

    // 4. Tạo các mảng dữ liệu cuối cùng, ánh xạ giá trị vào trục thời gian đã hợp nhất
    // Nếu không có giá trị cho một ngày, hãy điền `null`
    const finalHistoricalData = allUniqueLabels.map(
        (label) => historicalDataMap.get(label) || null
    );
    const finalPredictedData = allUniqueLabels.map(
        (label) => predictedDataMap.get(label) || null
    );

    const datasets = [];

    // Dataset cho dữ liệu dự đoán
    if (shouldShowPrediction && predicted.data.length > 0) {
        datasets.push({
        label: "Giá dự đoán",
        data: finalPredictedData,
        fill: true,
        borderColor: "rgb(255, 99, 132)",
        backgroundColor: "rgba(255, 99, 132, 0.2)",
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.4, // Làm cho đường cong mượt hơn
        borderDash: [5, 5],
        spanGaps: true, // Nối các điểm dữ liệu bị `null` ở giữa
        });
    }

    // Dataset cho dữ liệu lịch sử
    if (historical.data.length > 0) {
        datasets.push({
        label: shouldShowPrediction ? "Giá thực tế" : "Giá cổ phiếu",
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
        labels: allUniqueLabels, // Sử dụng trục thời gian đã được hợp nhất và sắp xếp
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
            maxRotation: 0, // Ngăn xoay nhãn
            autoSkip: true, // Tự động bỏ qua nhãn nếu quá dày
            maxTicksLimit: 10, // Giới hạn số lượng nhãn
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
                new Date(context[0].label).toLocaleDateString("vi-VN"),
            label: (context) =>
                `${context.dataset.label}: ${context.parsed.y.toLocaleString(
                "vi-VN"
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
