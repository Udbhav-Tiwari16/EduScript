%{
#include <stdio.h>
#include <stdlib.h>

int lexical_errors = 0;
%}

%option noyywrap
%option yylineno

/* Regular Definitions */
DIGIT       [0-9]
LETTER      [a-zA-Z_]
IDENTIFIER  {LETTER}({LETTER}|{DIGIT})*
INT_LIT     {DIGIT}+
FLOAT_LIT   {DIGIT}+\.{DIGIT}+
WHITESPACE  [ \t\r]+
NEWLINE     \n
COMMENT     \/\/[^\n]*

%%

{WHITESPACE}    { /* Ignore whitespace */ }
{NEWLINE}       { /* Tracked automatically by yylineno */ }
{COMMENT}       { /* Ignore single-line comments */ }

    /* Keywords */
"int"           { printf("%-10d | %-18s | %s\n", yylineno, "KW_INT", yytext); }
"float"         { printf("%-10d | %-18s | %s\n", yylineno, "KW_FLOAT", yytext); }
"if"            { printf("%-10d | %-18s | %s\n", yylineno, "KW_IF", yytext); }
"else"          { printf("%-10d | %-18s | %s\n", yylineno, "KW_ELSE", yytext); }
"while"         { printf("%-10d | %-18s | %s\n", yylineno, "KW_WHILE", yytext); }
"print"         { printf("%-10d | %-18s | %s\n", yylineno, "KW_PRINT", yytext); }

    /* Literals */
{FLOAT_LIT}     { printf("%-10d | %-18s | %s\n", yylineno, "LIT_FLOAT", yytext); }
{INT_LIT}       { printf("%-10d | %-18s | %s\n", yylineno, "LIT_INT", yytext); }

    /* Identifiers */
{IDENTIFIER}    { printf("%-10d | %-18s | %s\n", yylineno, "IDENTIFIER", yytext); }

    /* Relational Operators */
"=="            { printf("%-10d | %-18s | %s\n", yylineno, "OP_EQ", yytext); }
"!="            { printf("%-10d | %-18s | %s\n", yylineno, "OP_NEQ", yytext); }
"<="            { printf("%-10d | %-18s | %s\n", yylineno, "OP_LE", yytext); }
">="            { printf("%-10d | %-18s | %s\n", yylineno, "OP_GE", yytext); }
"<"             { printf("%-10d | %-18s | %s\n", yylineno, "OP_LT", yytext); }
">"             { printf("%-10d | %-18s | %s\n", yylineno, "OP_GT", yytext); }

    /* Assignment Operator */
"="             { printf("%-10d | %-18s | %s\n", yylineno, "OP_ASSIGN", yytext); }

    /* Arithmetic Operators */
"+"             { printf("%-10d | %-18s | %s\n", yylineno, "OP_ADD", yytext); }
"-"             { printf("%-10d | %-18s | %s\n", yylineno, "OP_SUB", yytext); }
"*"             { printf("%-10d | %-18s | %s\n", yylineno, "OP_MUL", yytext); }
"/"             { printf("%-10d | %-18s | %s\n", yylineno, "OP_DIV", yytext); }
"%"             { printf("%-10d | %-18s | %s\n", yylineno, "OP_MOD", yytext); }

    /* Delimiters */
"("             { printf("%-10d | %-18s | %s\n", yylineno, "DELIM_LPAREN", yytext); }
")"             { printf("%-10d | %-18s | %s\n", yylineno, "DELIM_RPAREN", yytext); }
"{"             { printf("%-10d | %-18s | %s\n", yylineno, "DELIM_LBRACE", yytext); }
"}"             { printf("%-10d | %-18s | %s\n", yylineno, "DELIM_RBRACE", yytext); }
";"             { printf("%-10d | %-18s | %s\n", yylineno, "DELIM_SEMICOLON", yytext); }
","             { printf("%-10d | %-18s | %s\n", yylineno, "DELIM_COMMA", yytext); }

    /* Lexical Error Handling */
.               {
                    lexical_errors++;
                    fprintf(stderr, "LEXICAL ERROR [Line %d]: Unsupported character '%s'\n", yylineno, yytext);
                }

%%

int main(int argc, char **argv) {
    if (argc > 1) {
        FILE *file = fopen(argv[1], "r");
        if (!file) {
            perror("Error opening input file");
            return 1;
        }
        yyin = file;
    }

    printf("====================================================\n");
    printf("%-10s | %-18s | %s\n", "Line No.", "Token Type", "Lexeme");
    printf("====================================================\n");

    yylex();

    printf("====================================================\n");
    if (lexical_errors > 0) {
        printf("Lexical Analysis Completed with %d error(s).\n", lexical_errors);
    } else {
        printf("Lexical Analysis Completed Successfully (0 errors).\n");
    }

    return 0;
}