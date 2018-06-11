SHARED_PATH=../../mission_server/

all:
	g++ -g -o test_single_request test_ms_sr.cpp $(SHARED_PATH)mission_server.cpp -I$(SHARED_PATH) -lproc

clean:
	rm test_single_request
