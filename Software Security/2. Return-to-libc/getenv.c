#include <stdlib.h>
#include <stdio.h>
#include <string.h> 
void main(int argc,char const *argv[]){
	char* shell = getenv("MYSHELL");
	if (shell)
		printf("%x\n", (unsigned int)shell);
}