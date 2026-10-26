import unittest,torch
from integer_reference import IntegerGraph,rshift,round_div

class GeometryTests(unittest.TestCase):
    def test_signed_nearest_even(self):
        x=torch.arange(-8191,8192,dtype=torch.int64)
        for shift in range(1,13):self.assertTrue(torch.equal(rshift(x,shift),torch.round(x.double()/(2**shift)).long()))
        self.assertEqual(round_div(-5,2),-2);self.assertEqual(round_div(-7,2),-4)
    def test_bilinear_is_exact_quarter_geometry(self):
        class Up(torch.nn.Module):
            def __init__(self):super().__init__();self.up=torch.nn.Upsample(scale_factor=2,mode='bilinear',align_corners=False)
            def forward(self,x):return self.up(x)
        graph=torch.fx.symbolic_trace(Up());ref=IntegerGraph(graph,dict(exponents={'up':-4}))
        for h,w in [(1,1),(1,7),(5,1),(7,11)]:
            x=torch.randint(-500,500,(1,3,h,w)).double();out=ref.run(x)
            self.assertTrue(torch.equal(out.q.double()/16,graph(x)))
    def test_pool_geometry(self):
        class Pool(torch.nn.Module):
            def __init__(self):super().__init__();self.pool=torch.nn.MaxPool2d(2,2)
            def forward(self,x):return self.pool(x)
        graph=torch.fx.symbolic_trace(Pool());ref=IntegerGraph(graph,dict(exponents={}))
        x=torch.randint(-500,500,(1,3,8,10)).double();out=ref.run(x)
        self.assertTrue(torch.equal(out.q.double(),graph(x)))
if __name__=='__main__':unittest.main()
