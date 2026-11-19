"""Run network searches without blocking the Tk event loop."""
import queue
import threading

from flight_search import find_ranked_flights_with_fallbacks

SEARCH_POLL_MS = 100

def enqueue_flight_search_result(request, result_queue):
    try:
        result_queue.put(find_ranked_flights_with_fallbacks(request))
    except Exception as error:
        result_queue.put(([], [f"Search could not be processed ({type(error).__name__})."]))


def poll_flight_search_queue(window, result_queue, request, on_result):
    try:
        results, notes = result_queue.get_nowait()
    except queue.Empty:
        window.after(SEARCH_POLL_MS, poll_flight_search_queue, window, result_queue, request, on_result)
        return
    on_result(results, notes, request)


def start_flight_search_in_background(window, request, on_result):
    result_queue = queue.Queue()
    threading.Thread(target=enqueue_flight_search_result, args=(request, result_queue), daemon=True).start()
    poll_flight_search_queue(window, result_queue, request, on_result)
