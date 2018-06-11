SHARED_PATH=../../mission_server/

all:
	g++ -g -o test_ms_1 test_overlap_ms_1.cpp $(SHARED_PATH)mission_server.cpp -I$(SHARED_PATH) -lproc
	g++ -g -o test_ms_2 test_overlap_ms_2.cpp $(SHARED_PATH)mission_server.cpp -I$(SHARED_PATH) -lproc

clean:
	rm test_ms_*
