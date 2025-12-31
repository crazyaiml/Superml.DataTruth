"""
Performance Benchmarking for DataTruth.

Measures latency, throughput, and resource usage across different
query types and scenarios.
"""

import time
import asyncio
import statistics
from typing import List, Dict
from datetime import datetime

from src.integration.orchestrator import QueryOrchestrator, QueryRequest
from src.optimizer.pagination import PaginationParams


class PerformanceBenchmark:
    """Benchmark suite for DataTruth performance."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        self.orchestrator = QueryOrchestrator()
        self.results: List[Dict] = []
    
    async def benchmark_simple_query(self, iterations: int = 10) -> Dict:
        """
        Benchmark simple aggregation query.
        
        Example: "What is the total revenue?"
        """
        query = "What is the total revenue in 2024?"
        latencies = []
        
        print(f"\n🔬 Benchmarking Simple Query ({iterations} iterations)")
        print(f"   Query: {query}")
        
        for i in range(iterations):
            request = QueryRequest(
                question=query,
                enable_caching=False  # Disable cache for fair comparison
            )
            
            start = time.time()
            response = await self.orchestrator.execute_query(request)
            end = time.time()
            
            latency = (end - start) * 1000  # Convert to ms
            latencies.append(latency)
            
            print(f"   Iteration {i+1}: {latency:.0f}ms")
        
        return self._calculate_stats(latencies, "Simple Query")
    
    async def benchmark_complex_query(self, iterations: int = 10) -> Dict:
        """
        Benchmark complex query with joins and aggregations.
        
        Example: "Show me top agents by revenue with their deal counts"
        """
        query = "Show me top 10 agents by revenue with deal counts in 2024"
        latencies = []
        
        print(f"\n🔬 Benchmarking Complex Query ({iterations} iterations)")
        print(f"   Query: {query}")
        
        for i in range(iterations):
            request = QueryRequest(
                question=query,
                enable_caching=False
            )
            
            start = time.time()
            response = await self.orchestrator.execute_query(request)
            end = time.time()
            
            latency = (end - start) * 1000
            latencies.append(latency)
            
            print(f"   Iteration {i+1}: {latency:.0f}ms")
        
        return self._calculate_stats(latencies, "Complex Query")
    
    async def benchmark_time_series_query(self, iterations: int = 10) -> Dict:
        """
        Benchmark time-series query with analytics.
        
        Example: "Show me monthly revenue for 2024"
        """
        query = "Show me monthly revenue for 2024 with trends"
        latencies = []
        
        print(f"\n🔬 Benchmarking Time-Series Query ({iterations} iterations)")
        print(f"   Query: {query}")
        
        for i in range(iterations):
            request = QueryRequest(
                question=query,
                enable_caching=False,
                enable_analytics=True
            )
            
            start = time.time()
            response = await self.orchestrator.execute_query(request)
            end = time.time()
            
            latency = (end - start) * 1000
            latencies.append(latency)
            
            print(f"   Iteration {i+1}: {latency:.0f}ms")
        
        return self._calculate_stats(latencies, "Time-Series Query")
    
    async def benchmark_paginated_query(self, iterations: int = 10) -> Dict:
        """
        Benchmark paginated query.
        
        Tests pagination overhead.
        """
        query = "Show me all agents"
        latencies = []
        
        print(f"\n🔬 Benchmarking Paginated Query ({iterations} iterations)")
        print(f"   Query: {query}")
        
        for i in range(iterations):
            pagination = PaginationParams(page=1, page_size=50)
            request = QueryRequest(
                question=query,
                pagination=pagination,
                enable_caching=False
            )
            
            start = time.time()
            response = await self.orchestrator.execute_query(request)
            end = time.time()
            
            latency = (end - start) * 1000
            latencies.append(latency)
            
            print(f"   Iteration {i+1}: {latency:.0f}ms")
        
        return self._calculate_stats(latencies, "Paginated Query")
    
    async def benchmark_cache_performance(self, iterations: int = 10) -> Dict:
        """
        Benchmark cache performance.
        
        Compares cold vs warm cache performance.
        """
        query = "What is the total revenue in 2024?"
        
        print(f"\n🔬 Benchmarking Cache Performance ({iterations} iterations)")
        print(f"   Query: {query}")
        
        # Cold cache (first request)
        print("\n   Testing Cold Cache:")
        request = QueryRequest(question=query, enable_caching=True)
        
        start = time.time()
        await self.orchestrator.execute_query(request)
        end = time.time()
        
        cold_latency = (end - start) * 1000
        print(f"   Cold cache: {cold_latency:.0f}ms")
        
        # Warm cache (subsequent requests)
        print("\n   Testing Warm Cache:")
        warm_latencies = []
        
        for i in range(iterations):
            start = time.time()
            await self.orchestrator.execute_query(request)
            end = time.time()
            
            latency = (end - start) * 1000
            warm_latencies.append(latency)
            print(f"   Iteration {i+1}: {latency:.0f}ms")
        
        warm_avg = statistics.mean(warm_latencies)
        speedup = cold_latency / warm_avg if warm_avg > 0 else 0
        
        return {
            "test": "Cache Performance",
            "cold_cache_ms": round(cold_latency, 2),
            "warm_cache_avg_ms": round(warm_avg, 2),
            "speedup": round(speedup, 2),
            "cache_effectiveness": f"{((1 - warm_avg/cold_latency) * 100):.1f}%"
        }
    
    async def benchmark_concurrent_requests(
        self,
        num_requests: int = 20
    ) -> Dict:
        """
        Benchmark concurrent request handling.
        
        Tests system throughput under concurrent load.
        """
        queries = [
            "What is the total revenue?",
            "Show me top 10 agents",
            "What is the average deal size?",
            "Show me revenue by region",
        ] * (num_requests // 4)
        
        print(f"\n🔬 Benchmarking Concurrent Requests ({num_requests} requests)")
        
        # Execute all requests concurrently
        tasks = []
        for query in queries:
            request = QueryRequest(question=query, enable_caching=False)
            task = self.orchestrator.execute_query(request)
            tasks.append(task)
        
        start = time.time()
        responses = await asyncio.gather(*tasks)
        end = time.time()
        
        total_time = (end - start) * 1000
        avg_latency = total_time / num_requests
        throughput = num_requests / (total_time / 1000)  # requests per second
        
        print(f"   Total time: {total_time:.0f}ms")
        print(f"   Avg latency per request: {avg_latency:.0f}ms")
        print(f"   Throughput: {throughput:.1f} requests/second")
        
        return {
            "test": "Concurrent Requests",
            "total_requests": num_requests,
            "total_time_ms": round(total_time, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "throughput_req_per_sec": round(throughput, 2)
        }
    
    async def benchmark_analytics_overhead(self, iterations: int = 10) -> Dict:
        """
        Benchmark analytics calculation overhead.
        
        Compares queries with vs without analytics.
        """
        query = "Show me monthly revenue for 2024"
        
        print(f"\n🔬 Benchmarking Analytics Overhead ({iterations} iterations)")
        print(f"   Query: {query}")
        
        # Without analytics
        print("\n   Testing Without Analytics:")
        without_latencies = []
        
        for i in range(iterations):
            request = QueryRequest(
                question=query,
                enable_caching=False,
                enable_analytics=False
            )
            
            start = time.time()
            await self.orchestrator.execute_query(request)
            end = time.time()
            
            latency = (end - start) * 1000
            without_latencies.append(latency)
            print(f"   Iteration {i+1}: {latency:.0f}ms")
        
        # With analytics
        print("\n   Testing With Analytics:")
        with_latencies = []
        
        for i in range(iterations):
            request = QueryRequest(
                question=query,
                enable_caching=False,
                enable_analytics=True
            )
            
            start = time.time()
            await self.orchestrator.execute_query(request)
            end = time.time()
            
            latency = (end - start) * 1000
            with_latencies.append(latency)
            print(f"   Iteration {i+1}: {latency:.0f}ms")
        
        without_avg = statistics.mean(without_latencies)
        with_avg = statistics.mean(with_latencies)
        overhead = with_avg - without_avg
        overhead_pct = (overhead / without_avg) * 100 if without_avg > 0 else 0
        
        return {
            "test": "Analytics Overhead",
            "without_analytics_ms": round(without_avg, 2),
            "with_analytics_ms": round(with_avg, 2),
            "overhead_ms": round(overhead, 2),
            "overhead_percentage": f"{overhead_pct:.1f}%"
        }
    
    def _calculate_stats(self, latencies: List[float], test_name: str) -> Dict:
        """Calculate statistics from latency measurements."""
        return {
            "test": test_name,
            "iterations": len(latencies),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
            "mean_ms": round(statistics.mean(latencies), 2),
            "median_ms": round(statistics.median(latencies), 2),
            "p95_ms": round(self._percentile(latencies, 0.95), 2),
            "p99_ms": round(self._percentile(latencies, 0.99), 2),
            "std_dev_ms": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _print_summary(self):
        """Print benchmark summary."""
        print("\n" + "="*80)
        print(" BENCHMARK SUMMARY")
        print("="*80)
        
        for result in self.results:
            print(f"\n📊 {result['test']}")
            print("-" * 80)
            
            for key, value in result.items():
                if key != "test":
                    # Format key nicely
                    formatted_key = key.replace("_", " ").title()
                    print(f"   {formatted_key:.<50} {value}")
        
        print("\n" + "="*80)
        print(" RECOMMENDATIONS")
        print("="*80)
        
        # Analyze results and provide recommendations
        for result in self.results:
            if result["test"] == "Simple Query" and result.get("median_ms", 0) > 2000:
                print("⚠️  Simple queries exceeding 2s target - consider query optimization")
            
            if result["test"] == "Cache Performance":
                speedup = result.get("speedup", 0)
                if speedup < 5:
                    print("⚠️  Cache speedup below 5x - verify Redis configuration")
                else:
                    print(f"✅ Cache speedup {speedup}x - excellent performance")
            
            if result["test"] == "Concurrent Requests":
                throughput = result.get("throughput_req_per_sec", 0)
                if throughput < 10:
                    print("⚠️  Low throughput - consider connection pooling or scaling")
                else:
                    print(f"✅ Throughput {throughput:.1f} req/s - good performance")
        
        print("\n" + "="*80)
    
    async def run_all_benchmarks(self):
        """Run all benchmark tests."""
        print("\n" + "="*80)
        print(" DATATRUTH PERFORMANCE BENCHMARK")
        print("="*80)
        print(f" Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        try:
            # Run each benchmark
            self.results.append(await self.benchmark_simple_query())
            self.results.append(await self.benchmark_complex_query())
            self.results.append(await self.benchmark_time_series_query())
            self.results.append(await self.benchmark_paginated_query())
            self.results.append(await self.benchmark_cache_performance())
            self.results.append(await self.benchmark_analytics_overhead())
            self.results.append(await self.benchmark_concurrent_requests())
            
            # Print summary
            self._print_summary()
            
        except Exception as e:
            print(f"\n❌ Benchmark failed: {str(e)}")
            import traceback
            traceback.print_exc()


async def main():
    """Run benchmark suite."""
    benchmark = PerformanceBenchmark()
    await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main())
