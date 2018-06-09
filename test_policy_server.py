from policy_server import PS
import sched, time

def test_ms_init():
   pass

def test_handle_request():
   policy_server = PS(sched.scheduler(time.time, time.sleep))
   policy_server.gs_set.add(0)

   time_request = [
      {"reqID": "12-0", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-1", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-2", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-3", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-4", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-5", "gsID": 0, "start": 0, "end":1, "wd": False},
   ]

   print policy_server.handle_requests(time_request, "abc")
   print 'hello'

def main():
   test_handle_request()

if __name__ == '__main__':
    main()