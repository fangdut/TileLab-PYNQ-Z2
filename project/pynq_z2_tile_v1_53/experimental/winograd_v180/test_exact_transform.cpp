// SPDX-License-Identifier: MIT
// Algebraic feasibility only; this is NOT the deployed detector or an HLS kernel.
#include <cstdint>
#include <cstdio>
static const int BT[4][4]={{1,0,-1,0},{0,1,1,0},{0,-1,1,0},{0,1,0,-1}};
static const int G2[4][3]={{2,0,0},{1,1,1},{1,-1,1},{0,0,2}};
static const int AT[2][4]={{1,1,1,0},{0,1,-1,-1}};
static unsigned cases=0;
static bool check(const int d[4][4],const int g[3][3]){
    int64_t v[4][4]={},u[4][4]={},m[4][4]={};
    for(int i=0;i<4;i++)for(int j=0;j<4;j++){
        for(int r=0;r<4;r++)for(int c=0;c<4;c++)v[i][j]+=int64_t(BT[i][r])*d[r][c]*BT[j][c];
        for(int r=0;r<3;r++)for(int c=0;c<3;c++)u[i][j]+=int64_t(G2[i][r])*g[r][c]*G2[j][c];
        m[i][j]=u[i][j]*v[i][j];
        if(v[i][j]<-512||v[i][j]>511||u[i][j]<-1152||u[i][j]>1152||m[i][j]<-589824||m[i][j]>589824)return false;
    }
    for(int y=0;y<2;y++)for(int x=0;x<2;x++){
        int64_t scaled=0,direct=0;
        for(int r=0;r<4;r++)for(int c=0;c<4;c++)scaled+=int64_t(AT[y][r])*m[r][c]*AT[x][c];
        for(int r=0;r<3;r++)for(int c=0;c<3;c++)direct+=int64_t(d[y+r][x+c])*g[r][c];
        // G2=2G, so the two-dimensional transform scales every output by4.
        if(scaled!=4*direct || scaled%4 || scaled<-(1LL<<23)||scaled>=(1LL<<23))return false;
    }
    ++cases;return true;
}
int main(){
    // Every basis-pair coefficient of the bilinear map:144 cases,576 outputs.
    // Equality here proves the unrounded integer polynomial identity.
    for(int p=0;p<16;p++)for(int q=0;q<9;q++){
        int d[4][4]={},g[3][3]={};d[p/4][p%4]=1;g[q/3][q%3]=1;
        if(!check(d,g))return 1;
    }
    for(int dp=0;dp<8;dp++)for(int gp=0;gp<8;gp++){
        int d[4][4],g[3][3];
        for(int y=0;y<4;y++)for(int x=0;x<4;x++)d[y][x]=((dp==0)||(dp>1&&((x+y*dp)&1)))?-128:127;
        for(int y=0;y<3;y++)for(int x=0;x<3;x++)g[y][x]=((gp==0)||(gp>1&&((x+y*gp)&1)))?-128:127;
        if(!check(d,g))return 2;
    }
    uint64_t state=0x184ea29cd817b603ULL;
    auto next=[&](){state^=state<<13;state^=state>>7;state^=state<<17;return state;};
    for(int n=0;n<100000;n++){
        int d[4][4],g[3][3];
        for(auto &row:d)for(auto &v:row)v=int(next()&255)-128;
        for(auto &row:g)for(auto &v:row)v=int(next()&255)-128;
        if(!check(d,g))return 3;
    }
    std::printf("EXACT_INTEGER_WINOGRAD_ALGEBRA_PASS cases=%u basis_coefficients=576 random_cases=100000\n",cases);
    return 0;
}
