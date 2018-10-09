//This file was generated from (Commercial) UPPAAL 4.0.14 (rev. 5615), May 2014

/*

*/
A[] not observer.FAILED

/*

*/
A[] not deadlock

/*

*/
(not observer.CONSISTENT) --> (observer.CONSISTENT)

/*

*/
(not (globalClock.CFP imply observer.CONSISTENT)) --> (globalClock.CFP imply observer.CONSISTENT)

/*

*/
A[] observer.CONSISTENT

/*

*/
A[] globalClock.CFP imply observer.CONSISTENT

/*

*/
A[] observer.inconsistentFor < T_MAXINCONS
