class Oracle { public static void main(String[] args) {
System.out.println(TinyAdd.add(0, 0));
System.out.println(TinyAdd.add(2, 3));
System.out.println(TinyAdd.add(-7, 4));
System.out.println(TinyAdd.add(-3, -9));
System.out.println(TinyAdd.add(2147483647, 0));
System.out.println(TinyAdd.add(2147483647, 1));
System.out.println(TinyAdd.add(-2147483648, -1));
System.out.println(TinyAdd.add(-2147483648, 2147483647));
}}
final class TinyAdd {
    public static int add(int a, int b) {
        return a + b;
    }
}
