class DecimalContract {
 public static void main(String[] args) {
  for (int i=0;i<65536;i++) {
   char c=(char)i;
   int n=Character.isDigit(c)?Character.getNumericValue(c):-1;
   System.out.print((char)(66+n));
  }
 }
}